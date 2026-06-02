const express = require('express');
const { randomUUID } = require('crypto');
const { body } = require('express-validator');
const { validate } = require('../middleware/validate');
const { requireAuth } = require('../middleware/auth');
const { extractApiKey } = require('../middleware/apiKey');
const { query } = require('../db/client');
const { injectEvent } = require('../services/simulationService');

const router = express.Router({ mergeParams: true });

router.post('/inject-event', requireAuth, extractApiKey,
  body('round_num').isInt({ min: 1 }),
  body('event_text').isString().notEmpty(),
  validate,
  async (req, res, next) => {
    try {
      const { round_num, event_text } = req.body;
      const eventId = randomUUID();
      await query(
        'INSERT INTO injected_events(id, simulation_id, round_num, event_text) VALUES($1,$2,$3,$4)',
        [eventId, req.params.id, round_num, event_text]
      );
      try {
        await injectEvent(req.params.id, { simulation_id: req.params.id, round_num, event_text }, req.apiKey);
      } catch { /* FastAPI offline OK in dev */ }
      res.status(201).json({ ok: true, event_id: eventId });
    } catch (err) { next(err); }
  }
);

router.get('/events', requireAuth, async (req, res, next) => {
  try {
    const { rows } = await query(
      'SELECT * FROM injected_events WHERE simulation_id=$1 ORDER BY round_num',
      [req.params.id]
    );
    res.json({ events: rows });
  } catch (err) { next(err); }
});

module.exports = router;
