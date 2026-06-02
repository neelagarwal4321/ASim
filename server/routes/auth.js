const express = require('express');
const bcrypt = require('bcrypt');
const crypto = require('crypto');
const rateLimit = require('express-rate-limit');
const { RedisStore } = require('rate-limit-redis');
const passport = require('passport');
const { body } = require('express-validator');
const { validate } = require('../middleware/validate');
const { requireAuth } = require('../middleware/auth');
const { query } = require('../db/client');
const { signAccess, signRefresh, verify } = require('../services/jwtService');
const { getClient } = require('../services/redisService');

const router = express.Router();

const authLimiter = rateLimit({
  windowMs: 60_000,
  max: 5,
  message: { error: 'Too many requests', code: 'RATE_LIMIT_AUTH' },
  store: new RedisStore({
    sendCommand: (...args) => getClient().call(...args),
    prefix: 'ratelimit:auth:',
  }),
});

async function issueStoredSession(user) {
  const role = user.role || 'free';
  const accessToken = signAccess({ userId: user.id, email: user.email, role });
  const refreshToken = signRefresh({ userId: user.id, jti: crypto.randomBytes(16).toString('hex') });
  const familyId = crypto.randomUUID();
  const tokenHash = crypto.createHash('sha256').update(refreshToken).digest('hex');
  const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
  await query(
    'INSERT INTO refresh_tokens(user_id, token_hash, expires_at, revoked, family_id) VALUES($1,$2,$3,$4,$5)',
    [user.id, tokenHash, expiresAt, false, familyId]
  );
  return { accessToken, refreshToken };
}

function issueDemoSession() {
  const demoId = `demo:${crypto.randomUUID()}`;
  const demoUser = { id: demoId, email: 'demo@asim.ai', name: 'Demo User', role: 'free' };
  return {
    accessToken: signAccess({ userId: demoId, email: demoUser.email, role: 'free', demo: true }),
    refreshToken: signRefresh({ userId: demoId, demo: true }),
    user: demoUser,
  };
}

async function issueOAuthCode(user) {
  const code = crypto.randomBytes(32).toString('hex');
  await getClient().set(
    `oauth:code:${code}`,
    JSON.stringify({ userId: user.id, email: user.email }),
    'EX', 60
  );
  const base = process.env.FRONTEND_URL || 'http://localhost:5173';
  return `${base}/auth/callback?code=${code}`;
}

router.post('/demo', (req, res) => {
  const session = issueDemoSession();
  res.json(session);
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
        'INSERT INTO users(email, password_hash, display_name) VALUES($1,$2,$3) RETURNING id, email, display_name, role',
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
      // Always run bcrypt regardless of whether user exists to prevent timing-based email enumeration
      const dummyHash = '$2b$12$invalidhashfortimingprotection00000000000000000000000000';
      const hash = rows[0]?.password_hash || dummyHash;
      const valid = await bcrypt.compare(password, hash);
      if (!rows.length || !valid) return res.status(401).json({ error: 'Invalid credentials', code: 'INVALID_CREDENTIALS' });
      const user = rows[0];
      const { accessToken, refreshToken } = await issueStoredSession(user);
      res.json({ accessToken, refreshToken, user: { id: user.id, email: user.email } });
    } catch (err) { next(err); }
  }
);

router.post('/refresh', async (req, res, next) => {
  try {
    const { refreshToken } = req.body;
    if (!refreshToken) return res.status(400).json({ error: 'refreshToken required', code: 'VALIDATION_ERROR' });
    let payload;
    try { payload = verify(refreshToken); } catch { return res.status(401).json({ error: 'Invalid refresh token', code: 'TOKEN_EXPIRED' }); }
    if (payload.demo) return res.json(issueDemoSession());

    const tokenHash = crypto.createHash('sha256').update(refreshToken).digest('hex');
    const { rows } = await query('SELECT * FROM refresh_tokens WHERE token_hash=$1', [tokenHash]);
    if (!rows.length) return res.status(401).json({ error: 'Refresh token not found', code: 'TOKEN_REVOKED' });

    const token = rows[0];
    if (new Date(token.expires_at) < new Date()) {
      return res.status(401).json({ error: 'Refresh token expired', code: 'TOKEN_EXPIRED' });
    }
    if (token.revoked) {
      // Reuse detection — revoke entire family
      if (token.family_id) {
        await query('UPDATE refresh_tokens SET revoked=true WHERE family_id=$1', [token.family_id]);
      }
      return res.status(401).json({ error: 'Token reuse detected — all sessions revoked', code: 'TOKEN_REVOKED' });
    }

    await query('UPDATE refresh_tokens SET revoked=true WHERE token_hash=$1', [tokenHash]);
    const userRows = await query('SELECT id, email, role FROM users WHERE id=$1', [payload.userId]);
    if (!userRows.rows.length) return res.status(401).json({ error: 'User not found', code: 'NOT_FOUND' });
    const user = userRows.rows[0];

    const newAccessToken = signAccess({ userId: user.id, email: user.email, role: user.role || 'free' });
    const newRefreshToken = signRefresh({ userId: user.id, jti: crypto.randomBytes(16).toString('hex') });
    const newHash = crypto.createHash('sha256').update(newRefreshToken).digest('hex');
    const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
    await query(
      'INSERT INTO refresh_tokens(user_id, token_hash, expires_at, revoked, family_id) VALUES($1,$2,$3,$4,$5)',
      [user.id, newHash, expiresAt, false, token.family_id]
    );
    res.json({ accessToken: newAccessToken, refreshToken: newRefreshToken });
  } catch (err) { next(err); }
});

router.post('/logout', requireAuth, async (req, res, next) => {
  try {
    const { refreshToken } = req.body;
    if (req.user.jti) {
      const ttl = req.user.exp ? req.user.exp - Math.floor(Date.now() / 1000) : 900;
      if (ttl >= 0) {
        await getClient().set(`jwt:revoked:${req.user.jti}`, '1', 'EX', Math.max(1, ttl));
      }
    }
    if (refreshToken) {
      const tokenHash = crypto.createHash('sha256').update(refreshToken).digest('hex');
      await query('UPDATE refresh_tokens SET revoked=true WHERE token_hash=$1', [tokenHash]);
    }
    res.json({ ok: true });
  } catch (err) { next(err); }
});

// /me lives on /api/v1/users/me — see routes/users.js (single source of truth).

// OAuth routes
router.get('/oauth/google', passport.authenticate('google', { scope: ['profile', 'email'], session: false }));
router.get('/oauth/google/callback',
  passport.authenticate('google', { session: false, failureRedirect: `${process.env.FRONTEND_URL || 'http://localhost:5173'}/login?error=oauth_failed` }),
  async (req, res, next) => {
    try {
      const redirectUrl = await issueOAuthCode(req.user);
      res.redirect(redirectUrl);
    } catch (err) { next(err); }
  }
);

router.get('/oauth/github', passport.authenticate('github', { scope: ['user:email'], session: false }));
router.get('/oauth/github/callback',
  passport.authenticate('github', { session: false, failureRedirect: `${process.env.FRONTEND_URL || 'http://localhost:5173'}/login?error=oauth_failed` }),
  async (req, res, next) => {
    try {
      const redirectUrl = await issueOAuthCode(req.user);
      res.redirect(redirectUrl);
    } catch (err) { next(err); }
  }
);

router.post('/exchange', async (req, res, next) => {
  try {
    const { code } = req.body;
    if (!code) return res.status(400).json({ error: 'code required' });
    const redis = getClient();
    const raw = await redis.get(`oauth:code:${code}`);
    if (!raw) return res.status(400).json({ error: 'Invalid or expired code' });
    await redis.del(`oauth:code:${code}`);
    const { userId, email } = JSON.parse(raw);
    const userRows = await query('SELECT id, email, display_name, role FROM users WHERE id=$1', [userId]);
    const user = userRows.rows[0];
    const { accessToken, refreshToken } = await issueStoredSession(user);
    res.json({ accessToken, refreshToken, user: { id: user.id, email: user.email, display_name: user.display_name } });
  } catch (err) { next(err); }
});

router.post('/forgot-password', authLimiter, async (req, res) => {
  // Stub — email service not yet integrated
  res.json({ ok: true, message: 'If that email exists, a reset link was sent.' });
});

router.post('/reset-password', async (req, res) => {
  // Stub
  res.json({ ok: true, message: 'Password reset stub — not yet implemented.' });
});

module.exports = router;
