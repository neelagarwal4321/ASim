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

test('refresh token has an expiry in the future', () => {
  const decoded = verify(signRefresh(payload));
  expect(decoded.exp).toBeGreaterThan(Math.floor(Date.now() / 1000));
});

test('signAccess embeds jti claim', () => {
  const decoded = verify(signAccess(payload));
  expect(typeof decoded.jti).toBe('string');
  expect(decoded.jti).toHaveLength(32); // 16 bytes hex
});
