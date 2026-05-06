function extractApiKey(req, res, next) {
  req.apiKey = req.headers['x-api-key'] || null;
  next();
}

module.exports = { extractApiKey };
