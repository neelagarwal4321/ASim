const { randomUUID } = require('crypto');

function requestId(req, res, next) {
  const provided = req.headers['x-request-id'];
  const id = (provided && provided.length <= 64 && provided.trim()) ? provided.trim() : randomUUID();
  req.requestId = id;
  res.setHeader('X-Request-ID', id);
  next();
}

module.exports = { requestId };
