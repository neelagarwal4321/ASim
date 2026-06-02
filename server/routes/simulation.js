const express = require('express');
const { body } = require('express-validator');
const { randomUUID } = require('crypto');
const { validate } = require('../middleware/validate');
const { requireAuth } = require('../middleware/auth');
const { extractApiKey } = require('../middleware/apiKey');
const { sanitizeScenario } = require('../middleware/sanitize');
const { query } = require('../db/client');
const { startSimulation, getSimulationStatus, controlSimulation } = require('../services/simulationService');
const { getTierLimits, checkAndIncrementDaily, checkAndIncrementActive } = require('../services/tierService');
const { getReport, setReport, invalidateReport } = require('../services/cacheService');

const router = express.Router();

/**
 * @openapi
 * /simulate:
 *   post:
 *     summary: Create and queue a simulation
 *     tags: [Simulations]
 *     security:
 *       - BearerAuth: []
 *       - ApiKeyAuth: []
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [scenario]
 *             properties:
 *               scenario: { type: string, maxLength: 2000 }
 *               agentCount: { type: integer, minimum: 1, maximum: 500, default: 50 }
 *               rounds: { type: integer, minimum: 1, maximum: 200, default: 5 }
 *               seed: { type: integer }
 *               webhookUrl: { type: string, format: uri }
 *     responses:
 *       201:
 *         description: Simulation queued
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 simulation_id: { type: string, format: uuid }
 *                 status: { type: string, example: queued }
 *                 estimated_cost: { type: number, example: 0.42 }
 *       422:
 *         description: Tier limit exceeded
 *         content:
 *           application/json:
 *             schema: { $ref: '#/components/schemas/Error' }
 *       429:
 *         description: Rate limit exceeded
 *         content:
 *           application/json:
 *             schema: { $ref: '#/components/schemas/Error' }
 */
router.post('/', requireAuth, extractApiKey, sanitizeScenario,
  body('scenario').isString().notEmpty().isLength({ max: 2000 }),
  body('agentCount').optional().isInt({ min: 1, max: 500 }),
  body('rounds').optional().isInt({ min: 1, max: 200 }),
  body('webhookUrl').optional().isURL(),
  validate,
  async (req, res, next) => {
    try {
      const { scenario, agentCount = 50, rounds = 5, seed, webhookUrl } = req.body;
      const role = req.user.role || 'free';
      const userId = req.user.userId;

      const limits = await getTierLimits(role);
      if (agentCount > limits.max_agents) {
        return res.status(422).json({ error: `Agent count exceeds ${role} limit of ${limits.max_agents}`, code: 'TIER_AGENT_LIMIT' });
      }
      if (rounds > limits.max_rounds) {
        return res.status(422).json({ error: `Rounds exceeds ${role} limit of ${limits.max_rounds}`, code: 'TIER_ROUND_LIMIT' });
      }

      const daily = await checkAndIncrementDaily(userId, role);
      if (!daily.ok) {
        return res.status(429)
          .set('X-RateLimit-Limit', String(limits.max_daily_sims))
          .set('X-RateLimit-Remaining', '0')
          .set('X-RateLimit-Reset', String(daily.reset || ''))
          .json({ error: 'Daily simulation quota exceeded', code: daily.code });
      }

      const active = await checkAndIncrementActive(userId, daily.limits);
      if (!active.ok) {
        return res.status(429).json({ error: 'Concurrent simulation limit reached', code: active.code });
      }

      // Cost estimate: agents × rounds × ~800 avg tokens × $0.000003/token
      const estimatedCost = parseFloat((agentCount * rounds * 800 * 0.000003).toFixed(4));

      const simulationId = randomUUID();
      await query(
        `INSERT INTO simulation_configs(id, user_id, scenario, agent_count, rounds, seed, status, webhook_url, estimated_cost)
         VALUES($1,$2,$3,$4,$5,$6,'pending',$7,$8)`,
        [simulationId, userId, scenario, agentCount, rounds, seed || null, webhookUrl || null, estimatedCost]
      );

      // Forward to FastAPI
      try {
        await startSimulation({
          simulation_id: simulationId,
          scenario,
          agent_count: agentCount,
          rounds,
          seed: seed || null,
          user_id: userId,
        }, req.apiKey);
        await query(`UPDATE simulation_configs SET status='running' WHERE id=$1`, [simulationId]);
      } catch (_) { /* FastAPI offline in dev — stays pending */ }

      res.status(201)
        .set('X-RateLimit-Limit', String(daily.limits.max_daily_sims))
        .set('X-RateLimit-Remaining', String(daily.remaining ?? daily.limits.max_daily_sims))
        .set('X-RateLimit-Reset', String(daily.reset || ''))
        .json({ simulation_id: simulationId, status: 'queued', estimated_cost: estimatedCost });
    } catch (err) { next(err); }
  }
);

/**
 * @openapi
 * /simulate:
 *   get:
 *     summary: List user simulations
 *     tags: [Simulations]
 *     parameters:
 *       - in: query
 *         name: page
 *         schema: { type: integer, default: 1 }
 *       - in: query
 *         name: limit
 *         schema: { type: integer, default: 20, maximum: 100 }
 *       - in: query
 *         name: status
 *         schema: { type: string, enum: [pending, running, complete, failed, cancelled] }
 *     responses:
 *       200:
 *         description: Paginated simulation list
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 data:
 *                   type: array
 *                   items: { $ref: '#/components/schemas/SimulationConfig' }
 *                 meta: { $ref: '#/components/schemas/PaginationMeta' }
 */
router.get('/', requireAuth, async (req, res, next) => {
  try {
    const page = Math.max(1, parseInt(req.query.page) || 1);
    const limit = Math.min(parseInt(req.query.limit) || 20, 100);
    const status = req.query.status || null;
    if (req.user.demo) {
      return res.json({ data: [], meta: { page, limit, total: 0, has_more: false } });
    }
    const offset = (page - 1) * limit;
    const statusClause = status ? 'AND status=$4' : '';
    const baseParams = status ? [req.user.userId, status] : [req.user.userId];
    const countRes = await query(
      `SELECT COUNT(*) FROM simulation_configs WHERE user_id=$1 AND deleted_at IS NULL ${statusClause}`,
      baseParams
    );
    const total = parseInt(countRes.rows[0].count, 10);
    const listParams = status
      ? [req.user.userId, status, limit, offset]
      : [req.user.userId, limit, offset];
    const { rows } = await query(
      `SELECT id, scenario, agent_count, rounds, status, estimated_cost, created_at
       FROM simulation_configs
       WHERE user_id=$1 AND deleted_at IS NULL ${status ? 'AND status=$2' : ''}
       ORDER BY created_at DESC LIMIT $${status ? 3 : 2} OFFSET $${status ? 4 : 3}`,
      listParams
    );
    res.json({ data: rows, meta: { page, limit, total, has_more: offset + rows.length < total } });
  } catch (err) { next(err); }
});

// GET /api/v1/simulate/:id
router.get('/:id', requireAuth, async (req, res, next) => {
  try {
    const cached = await getReport(req.params.id);
    if (cached && cached.user_id && cached.user_id === req.user.userId) return res.json(cached);

    const { rows } = await query(
      `SELECT sc.*, sr.verdict, sr.confidence, sr.distribution, sr.narrative,
              sr.counterfactuals, sr.report, sr.avg_stance, sr.hallucination_level
       FROM simulation_configs sc
       LEFT JOIN simulation_results sr ON sr.simulation_id = sc.id
       WHERE sc.id=$1 AND sc.user_id=$2 AND sc.deleted_at IS NULL`,
      [req.params.id, req.user.userId]
    );
    if (!rows.length) return res.status(404).json({ error: 'Simulation not found', code: 'NOT_FOUND' });
    const row = rows[0];
    if (row.status === 'complete') {
      setReport(req.params.id, row).catch(() => {});
    }
    res.json(row);
  } catch (err) { next(err); }
});

// DELETE /api/v1/simulate/:id — soft delete
router.delete('/:id', requireAuth, async (req, res, next) => {
  try {
    await query(
      `UPDATE simulation_configs SET deleted_at=NOW() WHERE id=$1 AND user_id=$2`,
      [req.params.id, req.user.userId]
    );
    invalidateReport(req.params.id).catch(() => {}); // non-fatal
    res.json({ ok: true });
  } catch (err) { next(err); }
});

// POST /api/v1/simulate/:id/control
router.post('/:id/control', requireAuth, extractApiKey,
  body('action').isIn(['pause', 'resume', 'cancel']),
  validate,
  async (req, res, next) => {
    try {
      await controlSimulation(req.params.id, req.body.action, req.apiKey);
      if (req.body.action === 'cancel') {
        await query(`UPDATE simulation_configs SET status='cancelled' WHERE id=$1`, [req.params.id]);
      }
      res.json({ ok: true });
    } catch (err) { next(err); }
  }
);

module.exports = router;
