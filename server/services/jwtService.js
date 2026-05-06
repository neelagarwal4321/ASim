const jwt = require('jsonwebtoken');

const SECRET = process.env.SECRET_KEY;

function signAccess(payload) {
  return jwt.sign(payload, SECRET, { expiresIn: '15m' });
}

function signRefresh(payload) {
  return jwt.sign(payload, SECRET, { expiresIn: '7d' });
}

function verify(token) {
  return jwt.verify(token, SECRET);
}

module.exports = { signAccess, signRefresh, verify };
