const logger = require('../services/logger');

const DB_UNAVAILABLE_CODES = new Set(['ECONNREFUSED', 'ENOTFOUND', 'ETIMEDOUT', 'ECONNRESET']);

function isDatabaseUnavailable(err) {
  return DB_UNAVAILABLE_CODES.has(err.code);
}

function errorHandler(err, req, res, next) {
  if (!err) return res.status(500).json({ error: 'Unknown error', code: 'INTERNAL_ERROR' });

  const status = err.status || err.statusCode || 500;
  const code = err.code || 'INTERNAL_ERROR';
  const message = status < 500 ? err.message : 'Internal server error';

  if (status >= 500) {
    logger.error({ err, requestId: req.requestId || 'unknown', path: req.path }, 'Unhandled error');
  }

  // Handle database unavailability as 503
  if (isDatabaseUnavailable(err)) {
    const isAuthRoute = req.path.startsWith('/api/v1/auth');
    return res.status(503).json({
      error: isAuthRoute ? 'Authentication service unavailable' : 'Database service unavailable',
    });
  }

  res.status(status).json({ error: message, code });
}

module.exports = { errorHandler };
