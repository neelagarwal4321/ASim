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

jest.mock('../services/redisService', () => ({
  getPublisher: jest.fn().mockReturnValue({ publish: jest.fn() }),
  getSubscriber: jest.fn().mockReturnValue({
    subscribe: jest.fn(),
    on: jest.fn(),
  }),
}));

const app = require('../index');
const { signAccess } = require('../services/jwtService');

const auth = () => ({ Authorization: `Bearer ${signAccess({ id: 'u1', email: 'a@b.com' })}` });

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
