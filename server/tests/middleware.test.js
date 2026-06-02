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

jest.mock('../services/redisService', () => {
  const client = {
    publish: jest.fn(),
    subscribe: jest.fn(),
    on: jest.fn(),
    get: jest.fn().mockResolvedValue(null),
    set: jest.fn().mockResolvedValue('OK'),
    exists: jest.fn().mockResolvedValue(0),
    call: jest.fn().mockResolvedValue(null),
  };
  return {
    getPublisher: jest.fn().mockReturnValue(client),
    getSubscriber: jest.fn().mockReturnValue(client),
    getClient: jest.fn().mockReturnValue(client),
  };
});

const app = require('../index');

function mkReqRes() {
  const req = { headers: {} };
  const res = { status: jest.fn().mockReturnThis(), json: jest.fn() };
  const next = jest.fn();
  return { req, res, next };
}

test('requireAuth calls next with valid token', async () => {
  const { req, res, next } = mkReqRes();
  req.headers.authorization = `Bearer ${signAccess({ id: 'u1', email: 'x@y.com' })}`;
  await requireAuth(req, res, next);
  expect(next).toHaveBeenCalled();
  expect(req.user.id).toBe('u1');
});

test('requireAuth returns 401 without header', async () => {
  const { req, res, next } = mkReqRes();
  await requireAuth(req, res, next);
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
