const request = require('supertest');

jest.mock('../db/client', () => ({
  query: jest.fn().mockResolvedValue({ rows: [] }),
  pool: { connect: jest.fn() },
}));

jest.mock('../services/simulationService', () => ({
  startSimulation: jest.fn().mockResolvedValue({ simulation_id: 'test-id' }),
  getSimulationStatus: jest.fn().mockResolvedValue({ status: 'running' }),
  controlSimulation: jest.fn().mockResolvedValue({ ok: true }),
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
const { signAccess } = require('../services/jwtService');
const { query } = require('../db/client');

const auth = () => ({ Authorization: `Bearer ${signAccess({ userId: 'u1', email: 'a@b.com', role: 'free' })}` });
const demoAuth = () => ({ Authorization: `Bearer ${signAccess({ userId: 'demo', email: 'demo@asim.ai', demo: true })}` });

beforeEach(() => {
  jest.clearAllMocks();
});

test('POST /api/v1/simulate 401 without auth', async () => {
  const r = await request(app).post('/api/v1/simulate').send({ scenario: 'test' });
  expect(r.status).toBe(401);
});

test('GET /api/v1/simulate 401 without auth', async () => {
  const r = await request(app).get('/api/v1/simulate');
  expect(r.status).toBe(401);
});

test('POST /api/v1/simulate 400 without scenario', async () => {
  const r = await request(app).post('/api/v1/simulate').set(auth()).send({});
  expect(r.status).toBe(400);
});

test('GET /api/v1/simulate returns empty list for demo session without database access', async () => {
  const r = await request(app).get('/api/v1/simulate?page=1&limit=5').set(demoAuth());

  expect(r.status).toBe(200);
  expect(r.body).toEqual({ simulations: [], page: 1, limit: 5 });
  expect(query).not.toHaveBeenCalled();
});
