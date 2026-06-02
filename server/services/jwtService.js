const jwt = require('jsonwebtoken');
const { randomBytes } = require('crypto');

const SECRET = process.env.SECRET_KEY;
if (!SECRET) {
  throw new Error('SECRET_KEY environment variable is required');
}

function signAccess(payload) {
  return jwt.sign(
    { ...payload, jti: randomBytes(16).toString('hex') },
    SECRET,
    { expiresIn: process.env.JWT_EXPIRY || '15m' }
  );
}

function signRefresh(payload) {
  return jwt.sign(payload, SECRET, { expiresIn: '7d' });
}

function verify(token) {
  return jwt.verify(token, SECRET);
}

module.exports = { signAccess, signRefresh, verify };
