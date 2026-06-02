const express = require('express');
const { body } = require('express-validator');
const { randomUUID } = require('crypto');
const { validate } = require('../middleware/validate');
const { requireAuth } = require('../middleware/auth');
const { extractApiKey } = require('../middleware/apiKey');
const { query } = require('../db/client');
const { startSimulation, getSimulationStatus, controlSimulation } = require('../services/simulationService');
const { getTierLimits, checkAndIncrementDaily, checkAndIncrementActive } = require('../services/tierService');

const router = express.Router();

// POST /api/v1/simulate — create + start simulation with tier enforcement
router.post('/', requireAuth, extractApiKey,
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

// GET /api/v1/simulate — list user simulations
router.get('/', requireAuth, async (req, res, next) => {
  try {
    const page = parseInt(req.query.page) || 1;
    const limit = Math.min(parseInt(req.query.limit) || 20, 100);
    if (req.user.demo) {
      return res.json({ simulations: [], page, limit });
    }
    const offset = (page - 1) * limit;
    const { rows } = await query(
      `SELECT id, scenario, agent_count, rounds, status, created_at
       FROM simulation_configs
       WHERE user_id=$1 AND deleted_at IS NULL
       ORDER BY created_at DESC LIMIT $2 OFFSET $3`,
      [req.user.userId, limit, offset]
    );
    res.json({ simulations: rows, page, limit });
  } catch (err) { next(err); }
});

// GET /api/v1/simulate/:id
router.get('/:id', requireAuth, async (req, res, next) => {
  try {
    const { rows } = await query(
      `SELECT sc.*, sr.verdict, sr.confidence, sr.distribution, sr.narrative,
              sr.counterfactuals, sr.report, sr.avg_stance
       FROM simulation_configs sc
       LEFT JOIN simulation_results sr ON sr.simulation_id = sc.id
       WHERE sc.id=$1 AND sc.user_id=$2 AND sc.deleted_at IS NULL`,
      [req.params.id, req.user.userId]
    );
    if (!rows.length) return res.status(404).json({ error: 'Simulation not found' });
    res.json(rows[0]);
  } catch (err) { next(err); }
});

// DELETE /api/v1/simulate/:id — soft delete
router.delete('/:id', requireAuth, async (req, res, next) => {
  try {
    await query(
      `UPDATE simulation_configs SET deleted_at=NOW() WHERE id=$1 AND user_id=$2`,
      [req.params.id, req.user.userId]
    );
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
