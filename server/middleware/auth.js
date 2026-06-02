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
  if (payload.jti) {
    const revoked = await getClient().exists(`jwt:revoked:${payload.jti}`);
    if (revoked) {
      return res.status(401).json({ error: 'Token has been revoked', code: 'TOKEN_REVOKED' });
    }
  }
  req.user = payload;
  next();
}

module.exports = { requireAuth };
