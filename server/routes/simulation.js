const express = require('express');
const { body } = require('express-validator');
const { validate } = require('../middleware/validate');
const { requireAuth } = require('../middleware/auth');
const { extractApiKey } = require('../middleware/apiKey');
const { query } = require('../db/client');
const { startSimulation, getSimulationStatus, controlSimulation } = require('../services/simulationService');

const router = express.Router();

function newUUID() { return require('crypto').randomUUID(); }

// POST /api/v1/simulate — create + start simulation
router.post('/', requireAuth, extractApiKey,
  body('scenario').isString().notEmpty(),
  body('agentCount').optional().isInt({ min: 1, max: 500 }),
  body('rounds').optional().isInt({ min: 1, max: 20 }),
  validate,
  async (req, res, next) => {
    try {
      const { scenario, agentCount = 50, rounds = 5, seed } = req.body;
      const simulationId = newUUID();

      // Persist config to Postgres
      await query(
        `INSERT INTO simulation_configs(id, user_id, scenario, agent_count, rounds, seed, status)
         VALUES($1,$2,$3,$4,$5,$6,'pending')`,
        [simulationId, req.user.userId, scenario, agentCount, rounds, seed || null]
      );

      // Forward to FastAPI
      try {
        await startSimulation({
          simulation_id: simulationId,
          scenario,
          agent_count: agentCount,
          rounds,
          seed: seed || null,
        }, req.apiKey);
        await query(`UPDATE simulation_configs SET status='running' WHERE id=$1`, [simulationId]);
      } catch (fastapiErr) {
        // FastAPI offline is OK in dev — mark as pending
      }

      res.status(201).json({ simulation_id: simulationId });
    } catch (err) { next(err); }
  }
);

// GET /api/v1/simulate — list user simulations
router.get('/', requireAuth, async (req, res, next) => {
  try {
    const page = parseInt(req.query.page) || 1;
    const limit = Math.min(parseInt(req.query.limit) || 20, 100);
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
      `SELECT sc.*, sr.verdict, sr.confidence, sr.distribution, sr.narrative
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
router.post('/:id/control', requireAuth,
  body('action').isIn(['pause', 'resume', 'cancel']),
  validate,
  async (req, res, next) => {
    try {
      await controlSimulation(req.params.id, req.body.action);
      if (req.body.action === 'cancel') {
        await query(`UPDATE simulation_configs SET status='cancelled' WHERE id=$1`, [req.params.id]);
      }
      res.json({ ok: true });
    } catch (err) { next(err); }
  }
);

module.exports = router;
