const logger = require('../services/logger');

function errorHandler(err, req, res, next) {
  logger.error('Unhandled error: %s %s — %s', req.method, req.path, err.message, { stack: err.stack });
  res.status(err.status || 500).json({ error: 'Internal server error' });
}

module.exports = { errorHandler };
