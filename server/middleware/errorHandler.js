const logger = require('../services/logger');

function isDatabaseUnavailable(err) {
  return ['ECONNREFUSED', 'ENOTFOUND', 'ETIMEDOUT', 'ECONNRESET'].includes(err.code);
}

function errorHandler(err, req, res, next) {
  logger.error(`Unhandled error: ${req.method} ${req.path} - ${err.message}`, { stack: err.stack, code: err.code });
  if (isDatabaseUnavailable(err)) {
    const isAuthRoute = req.originalUrl?.startsWith('/api/v1/auth') || req.path.startsWith('/api/v1/auth');
    return res.status(503).json({
      error: isAuthRoute ? 'Authentication service unavailable' : 'Database service unavailable',
    });
  }
  res.status(err.status || 500).json({ error: 'Internal server error' });
}

module.exports = { errorHandler };
