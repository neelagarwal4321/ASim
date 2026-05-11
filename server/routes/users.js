const express = require('express');
const { body } = require('express-validator');
const { validate } = require('../middleware/validate');
const { requireAuth } = require('../middleware/auth');
const { query } = require('../db/client');

const router = express.Router();

router.get('/me', requireAuth, async (req, res, next) => {
  try {
    const { rows } = await query(
      'SELECT id, email, display_name, avatar_url, created_at FROM users WHERE id=$1 AND deleted_at IS NULL',
      [req.user.userId]
    );
    if (!rows.length) return res.status(404).json({ error: 'User not found' });
    res.json(rows[0]);
  } catch (err) { next(err); }
});

router.patch('/me', requireAuth,
  body('display_name').optional().isString().isLength({ max: 100 }),
  validate,
  async (req, res, next) => {
    try {
      const { display_name } = req.body;
      const { rows } = await query(
        'UPDATE users SET display_name=$1, updated_at=NOW() WHERE id=$2 RETURNING id, email, display_name',
        [display_name, req.user.userId]
      );
      res.json(rows[0]);
    } catch (err) { next(err); }
  }
);

// API key routes — never store in DB, only in Redis via FastAPI
router.post('/me/api-key', requireAuth, async (req, res) => {
  // Actual encryption happens in FastAPI services/api_key_store.py
  // Node just acknowledges — key is forwarded as X-API-Key header on sim start
  res.json({ ok: true, message: 'API key stored (use X-API-Key header on simulation requests)' });
});

router.delete('/me/api-key', requireAuth, async (req, res) => {
  res.json({ ok: true });
});

// Soft-delete the account and revoke all refresh tokens so existing sessions end.
router.delete('/me', requireAuth, async (req, res, next) => {
  try {
    if (req.user.demo) return res.status(403).json({ error: 'Demo accounts cannot be deleted' });
    await query('UPDATE users SET deleted_at=NOW(), updated_at=NOW() WHERE id=$1', [req.user.userId]);
    await query('UPDATE refresh_tokens SET revoked=true WHERE user_id=$1 AND revoked=false', [req.user.userId]);
    res.json({ ok: true });
  } catch (err) { next(err); }
});

module.exports = router;
