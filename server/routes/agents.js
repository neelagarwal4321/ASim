const express = require('express');
const { requireAuth } = require('../middleware/auth');
const { query } = require('../db/client');

const router = express.Router({ mergeParams: true });

router.get('/', requireAuth, async (req, res, next) => {
  try {
    // Verify sim ownership before returning agents
    const simCheck = await query(
      'SELECT id FROM simulation_configs WHERE id=$1 AND user_id=$2 AND deleted_at IS NULL',
      [req.params.id, req.user.userId]
    );
    if (!simCheck.rows.length) return res.status(404).json({ error: 'Simulation not found', code: 'NOT_FOUND' });

    const { rows } = await query(
      'SELECT * FROM agent_profiles WHERE simulation_id=$1',
      [req.params.id]
    );
    res.json({ agents: rows });
  } catch (err) { next(err); }
});

router.get('/:agentId', requireAuth, async (req, res, next) => {
  try {
    // Verify sim ownership before returning agent
    const simCheck = await query(
      'SELECT id FROM simulation_configs WHERE id=$1 AND user_id=$2 AND deleted_at IS NULL',
      [req.params.id, req.user.userId]
    );
    if (!simCheck.rows.length) return res.status(404).json({ error: 'Simulation not found', code: 'NOT_FOUND' });

    const { rows } = await query(
      'SELECT * FROM agent_profiles WHERE id=$1 AND simulation_id=$2',
      [req.params.agentId, req.params.id]
    );
    if (!rows.length) return res.status(404).json({ error: 'Agent not found' });
    res.json(rows[0]);
  } catch (err) { next(err); }
});

module.exports = router;
