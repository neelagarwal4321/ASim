const request = require('supertest');

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
  del: jest.fn().mockResolvedValue(1),
  incr: jest.fn().mockResolvedValue(1),
  decr: jest.fn().mockResolvedValue(0),
  expire: jest.fn().mockResolvedValue(1),
  expireat: jest.fn().mockResolvedValue(1),
  call: jest.fn().mockResolvedValue(null),
};

jest.mock('../services/redisService', () => ({
  getPublisher: jest.fn().mockReturnValue(mockRedisClient),
  getSubscriber: jest.fn().mockReturnValue(mockRedisClient),
  getClient: jest.fn().mockReturnValue(mockRedisClient),
}));

const app = require('../index');
const { query } = require('../db/client');
const { verify } = require('../services/jwtService');

beforeEach(() => {
  jest.clearAllMocks();
});

test('POST /api/v1/auth/signup 400 when no email', async () => {
  const r = await request(app).post('/api/v1/auth/signup').send({ password: 'password123' });
  expect(r.status).toBe(400);
});

test('POST /api/v1/auth/login 400 when empty body', async () => {
  const r = await request(app).post('/api/v1/auth/login').send({});
  expect(r.status).toBe(400);
});

test('GET /api/v1/users/me 401 without token', async () => {
  const r = await request(app).get('/api/v1/users/me');
  expect(r.status).toBe(401);
});

test('POST /api/v1/auth/login 503 when database is unavailable', async () => {
  const err = new Error('connect ECONNREFUSED 127.0.0.1:5432');
  err.code = 'ECONNREFUSED';
  query.mockRejectedValueOnce(err);

  const r = await request(app)
    .post('/api/v1/auth/login')
    .send({ email: 'jane@example.com', password: 'password123' });

  expect(r.status).toBe(503);
  expect(r.body).toEqual({ error: 'Authentication service unavailable' });
});

test('POST /api/v1/auth/demo returns signed demo session without database access', async () => {
  const r = await request(app).post('/api/v1/auth/demo').send();

  expect(r.status).toBe(200);
  expect(r.body.user).toEqual({ id: 'demo', email: 'demo@asim.ai', name: 'Demo User' });
  expect(r.body.accessToken).toBeTruthy();
  expect(r.body.refreshToken).toBeTruthy();
  expect(verify(r.body.accessToken)).toMatchObject({ userId: 'demo', email: 'demo@asim.ai', demo: true });
  expect(query).not.toHaveBeenCalled();
});

test('POST /api/v1/auth/refresh rotates demo tokens without database access', async () => {
  const refreshToken = require('../services/jwtService').signRefresh({ userId: 'demo', demo: true });

  const r = await request(app).post('/api/v1/auth/refresh').send({ refreshToken });

  expect(r.status).toBe(200);
  expect(r.body.accessToken).toBeTruthy();
  expect(r.body.refreshToken).toBeTruthy();
  expect(verify(r.body.accessToken)).toMatchObject({ userId: 'demo', email: 'demo@asim.ai', demo: true });
  expect(query).not.toHaveBeenCalled();
});
