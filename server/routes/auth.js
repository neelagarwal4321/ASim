const express = require('express');
const bcrypt = require('bcrypt');
const crypto = require('crypto');
const rateLimit = require('express-rate-limit');
const passport = require('passport');
const { body } = require('express-validator');
const { validate } = require('../middleware/validate');
const { requireAuth } = require('../middleware/auth');
const { query } = require('../db/client');
const { signAccess, signRefresh, verify } = require('../services/jwtService');

const router = express.Router();

const authLimiter = rateLimit({ windowMs: 60_000, max: 5, message: { error: 'Too many requests' } });
const DEMO_USER = { id: 'demo', email: 'demo@asim.ai', name: 'Demo User' };

async function issueStoredSession(user) {
  const accessToken = signAccess({ userId: user.id, email: user.email });
  const refreshToken = signRefresh({ userId: user.id });
  const tokenHash = crypto.createHash('sha256').update(refreshToken).digest('hex');
  const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
  await query('INSERT INTO refresh_tokens(user_id, token_hash, expires_at, revoked) VALUES($1,$2,$3,$4)', [user.id, tokenHash, expiresAt, false]);
  return { accessToken, refreshToken };
}

function issueDemoSession() {
  return {
    accessToken: signAccess({ userId: DEMO_USER.id, email: DEMO_USER.email, demo: true }),
    refreshToken: signRefresh({ userId: DEMO_USER.id, demo: true }),
  };
}

function getFrontendCallbackBase() {
  return process.env.FRONTEND_URL || process.env.OAUTH_FRONTEND_CALLBACK_BASE || 'http://localhost:5173';
}

function buildOAuthSuccessRedirect(user, accessToken, refreshToken) {
  const url = new URL('/auth/callback', getFrontendCallbackBase());
  url.searchParams.set('accessToken', accessToken);
  url.searchParams.set('refreshToken', refreshToken);
  url.searchParams.set('email', user.email);
  if (user.display_name || user.name) url.searchParams.set('name', user.display_name || user.name);
  return url.toString();
}

router.post('/demo', (req, res) => {
  const { accessToken, refreshToken } = issueDemoSession();
  res.json({ accessToken, refreshToken, user: DEMO_USER });
});

router.post('/signup', authLimiter,
  body('email').isEmail().normalizeEmail(),
  body('password').isLength({ min: 8 }),
  validate,
  async (req, res, next) => {
    try {
      const { email, password, display_name } = req.body;
      const existing = await query('SELECT id FROM users WHERE email=$1', [email]);
      if (existing.rows.length) return res.status(409).json({ error: 'Email already registered' });

      const password_hash = await bcrypt.hash(password, 12);
      const { rows } = await query(
        'INSERT INTO users(email, password_hash, display_name) VALUES($1,$2,$3) RETURNING id, email, display_name',
        [email, password_hash, display_name || null]
      );
      const user = rows[0];
      const { accessToken, refreshToken } = await issueStoredSession(user);
      res.status(201).json({ accessToken, refreshToken, user: { id: user.id, email: user.email, display_name: user.display_name } });
    } catch (err) { next(err); }
  }
);

router.post('/login', authLimiter,
  body('email').isEmail().normalizeEmail(),
  body('password').notEmpty(),
  validate,
  async (req, res, next) => {
    try {
      const { email, password } = req.body;
      const { rows } = await query('SELECT * FROM users WHERE email=$1 AND deleted_at IS NULL', [email]);
      if (!rows.length || !rows[0].password_hash) return res.status(401).json({ error: 'Invalid credentials' });
      const valid = await bcrypt.compare(password, rows[0].password_hash);
      if (!valid) return res.status(401).json({ error: 'Invalid credentials' });
      const user = rows[0];
      const { accessToken, refreshToken } = await issueStoredSession(user);
      res.json({ accessToken, refreshToken, user: { id: user.id, email: user.email } });
    } catch (err) { next(err); }
  }
);

router.post('/refresh', async (req, res, next) => {
  try {
    const { refreshToken } = req.body;
    if (!refreshToken) return res.status(400).json({ error: 'refreshToken required' });
    let payload;
    try { payload = verify(refreshToken); } catch { return res.status(401).json({ error: 'Invalid refresh token' }); }
    if (payload.demo) {
      return res.json(issueDemoSession());
    }
    const tokenHash = crypto.createHash('sha256').update(refreshToken).digest('hex');
    const { rows } = await query(
      'SELECT * FROM refresh_tokens WHERE token_hash=$1 AND revoked=false AND expires_at > NOW()',
      [tokenHash]
    );
    if (!rows.length) return res.status(401).json({ error: 'Refresh token revoked or expired' });
    await query('UPDATE refresh_tokens SET revoked=true WHERE token_hash=$1', [tokenHash]);
    const userRows = await query('SELECT id, email FROM users WHERE id=$1', [payload.userId]);
    if (!userRows.rows.length) return res.status(401).json({ error: 'User not found' });
    const user = userRows.rows[0];
    const tokens = await issueStoredSession(user);
    res.json(tokens);
  } catch (err) { next(err); }
});

router.post('/logout', requireAuth, async (req, res, next) => {
  try {
    const { refreshToken } = req.body;
    if (refreshToken) {
      const tokenHash = crypto.createHash('sha256').update(refreshToken).digest('hex');
      await query('UPDATE refresh_tokens SET revoked=true WHERE token_hash=$1', [tokenHash]);
    }
    res.json({ ok: true });
  } catch (err) { next(err); }
});

router.get('/me', requireAuth, async (req, res, next) => {
  try {
    const { rows } = await query('SELECT id, email, display_name, avatar_url, created_at FROM users WHERE id=$1', [req.user.userId]);
    if (!rows.length) return res.status(404).json({ error: 'User not found' });
    res.json(rows[0]);
  } catch (err) { next(err); }
});

// OAuth routes
router.get('/oauth/google', passport.authenticate('google', { scope: ['profile', 'email'], session: false }));
router.get('/oauth/google/callback',
  passport.authenticate('google', { session: false, failureRedirect: '/login?error=oauth_failed' }),
  async (req, res, next) => {
    try {
      const { accessToken, refreshToken } = await issueStoredSession(req.user);
      res.redirect(buildOAuthSuccessRedirect(req.user, accessToken, refreshToken));
    } catch (err) { next(err); }
  }
);

router.get('/oauth/github', passport.authenticate('github', { scope: ['user:email'], session: false }));
router.get('/oauth/github/callback',
  passport.authenticate('github', { session: false, failureRedirect: '/login?error=oauth_failed' }),
  async (req, res, next) => {
    try {
      const { accessToken, refreshToken } = await issueStoredSession(req.user);
      res.redirect(buildOAuthSuccessRedirect(req.user, accessToken, refreshToken));
    } catch (err) { next(err); }
  }
);

router.post('/forgot-password', authLimiter, async (req, res) => {
  // Stub — email service not yet integrated
  res.json({ ok: true, message: 'If that email exists, a reset link was sent.' });
});

router.post('/reset-password', async (req, res) => {
  // Stub
  res.json({ ok: true, message: 'Password reset stub — not yet implemented.' });
});

module.exports = router;
