const { verify } = require('../services/jwtService');
const { getClient } = require('../services/redisService');

async function requireAuth(req, res, next) {
  const header = req.headers.authorization;
  if (!header || !header.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing or invalid authorization header', code: 'AUTH_REQUIRED' });
  }
  let payload;
  try {
    payload = verify(header.slice(7));
  } catch {
    return res.status(401).json({ error: 'Invalid or expired token', code: 'TOKEN_EXPIRED' });
  }
  if (payload.jti && !payload.demo) {
    try {
      const revoked = await getClient().exists(`jwt:revoked:${payload.jti}`);
      if (revoked === 1) {
        return res.status(401).json({ error: 'Token has been revoked', code: 'TOKEN_REVOKED' });
      }
    } catch (err) {
      const logger = require('../services/logger');
      logger.error({ err }, 'Redis unavailable for JWT blacklist check — rejecting request');
      return res.status(503).json({ error: 'Service temporarily unavailable', code: 'SERVICE_UNAVAILABLE' });
    }
  } else if (payload.jti && payload.demo) {
    // Demo tokens are never blacklisted — skip Redis round-trip
    req.user = payload;
    return next();
  }
  req.user = payload;
  next();
}

module.exports = { requireAuth };
