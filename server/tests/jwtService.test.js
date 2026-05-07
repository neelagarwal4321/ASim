const { signAccess, signRefresh, verify } = require('../services/jwtService');
const payload = { id: 'u1', email: 'a@b.com' };

test('signAccess returns a JWT string', () => {
  expect(signAccess(payload).split('.')).toHaveLength(3);
});

test('verify decodes a valid token', () => {
  const decoded = verify(signAccess(payload));
  expect(decoded.id).toBe('u1');
});

test('verify throws on bad token', () => {
  expect(() => verify('bad.token.here')).toThrow();
});

test('refresh token expires later than access token', () => {
  expect(verify(signRefresh(payload)).exp).toBeGreaterThan(verify(signAccess(payload)).exp);
});
