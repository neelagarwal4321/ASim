const request = require('supertest');

jest.mock('../db/client', () => ({
  query: jest.fn().mockResolvedValue({ rows: [] }),
  pool: { connect: jest.fn() },
}));

jest.mock('../services/redisService', () => ({
  getPublisher: jest.fn().mockReturnValue({ publish: jest.fn() }),
  getSubscriber: jest.fn().mockReturnValue({
    subscribe: jest.fn(),
    on: jest.fn(),
  }),
}));

const app = require('../index');

test('POST /api/v1/auth/signup 400 when no email', async () => {
  const r = await request(app).post('/api/v1/auth/signup').send({ password: 'password123' });
  expect(r.status).toBe(400);
});

test('POST /api/v1/auth/login 400 when empty body', async () => {
  const r = await request(app).post('/api/v1/auth/login').send({});
  expect(r.status).toBe(400);
});

test('GET /api/v1/auth/me 401 without token', async () => {
  const r = await request(app).get('/api/v1/auth/me');
  expect(r.status).toBe(401);
});
