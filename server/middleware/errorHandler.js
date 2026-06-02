const logger = require('../services/logger');

function isDatabaseUnavailable(err) {
  return ['ECONNREFUSED', 'ENOTFOUND', 'ETIMEDOUT', 'ECONNRESET'].includes(err.code);
}

function errorHandler(err, req, res, next) {
  const status = err.status || err.statusCode || 500;
  const code = err.code || 'INTERNAL_ERROR';
  const message = status < 500 ? err.message : 'Internal server error';

  if (status >= 500) {
    logger.error({ err, requestId: req.requestId, path: req.path }, 'Unhandled error');
  }

  // Handle database unavailability as 503
  if (isDatabaseUnavailable(err)) {
    const isAuthRoute = req.originalUrl?.startsWith('/api/v1/auth') || req.path.startsWith('/api/v1/auth');
    return res.status(503).json({
      error: isAuthRoute ? 'Authentication service unavailable' : 'Database service unavailable',
    });
  }

  res.status(status).json({ error: message, code });
}

module.exports = { errorHandler };
