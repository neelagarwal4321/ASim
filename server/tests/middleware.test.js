const request = require('supertest');
const { signAccess } = require('../services/jwtService');
const { requireAuth } = require('../middleware/auth');
const { extractApiKey } = require('../middleware/apiKey');

jest.mock('../db/client', () => ({
  query: jest.fn().mockResolvedValue({ rows: [] }),
  pool: { connect: jest.fn() },
}));

jest.mock('rate-limit-redis', () => ({
  RedisStore: jest.fn().mockImplementation(() => ({
    init: jest.fn().mockResolvedValue(undefined),
    increment: jest.fn().mockResolvedValue({ totalHits: 1, resetTime: new Date() }),
    decrement: jest.fn().mockResolvedValue(undefined),
    resetKey: jest.fn().mockResolvedValue(undefined),
  })),
}));

const mockRedisClient = {
  publish: jest.fn(),
  subscribe: jest.fn(),
  on: jest.fn(),
  get: jest.fn().mockResolvedValue(null),
  set: jest.fn().mockResolvedValue('OK'),
  call: jest.fn().mockResolvedValue(null),
};

jest.mock('../services/redisService', () => ({
  getPublisher: jest.fn().mockReturnValue(mockRedisClient),
  getSubscriber: jest.fn().mockReturnValue(mockRedisClient),
  getClient: jest.fn().mockReturnValue(mockRedisClient),
}));

const app = require('../index');

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

test('attaches X-Request-ID to every response', async () => {
  const res = await request(app).get('/health');
  expect(res.headers['x-request-id']).toMatch(/^[0-9a-f-]{36}$/);
});

test('echoes client-provided X-Request-ID', async () => {
  const id = 'test-req-123';
  const res = await request(app).get('/health').set('X-Request-ID', id);
  expect(res.headers['x-request-id']).toBe(id);
});
