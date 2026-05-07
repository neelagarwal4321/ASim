const { signAccess } = require('../services/jwtService');
const { requireAuth } = require('../middleware/auth');
const { extractApiKey } = require('../middleware/apiKey');

function mkReqRes() {
  const req = { headers: {} };
  const res = { status: jest.fn().mockReturnThis(), json: jest.fn() };
  const next = jest.fn();
  return { req, res, next };
}

test('requireAuth calls next with valid token', () => {
  const { req, res, next } = mkReqRes();
  req.headers.authorization = `Bearer ${signAccess({ id: 'u1', email: 'x@y.com' })}`;
  requireAuth(req, res, next);
  expect(next).toHaveBeenCalled();
  expect(req.user.id).toBe('u1');
});

test('requireAuth returns 401 without header', () => {
  const { req, res, next } = mkReqRes();
  requireAuth(req, res, next);
  expect(res.status).toHaveBeenCalledWith(401);
});

test('extractApiKey sets req.apiKey from header', () => {
  const { req, res, next } = mkReqRes();
  req.headers['x-api-key'] = 'sk-123';
  extractApiKey(req, res, next);
  expect(req.apiKey).toBe('sk-123');
});

test('extractApiKey sets null when header absent', () => {
  const { req, res, next } = mkReqRes();
  extractApiKey(req, res, next);
  expect(req.apiKey).toBeNull();
});
