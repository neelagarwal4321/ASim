const { getClient } = require('./redisService');

async function getReport(simId) {
  const cached = await getClient().get(`cache:report:${simId}`);
  return cached ? JSON.parse(cached) : null;
}

async function setReport(simId, data) {
  await getClient().set(`cache:report:${simId}`, JSON.stringify(data), 'EX', 21600); // 6h
}

async function invalidateReport(simId) {
  await getClient().del(`cache:report:${simId}`);
}

async function getUserProfile(userId) {
  const cached = await getClient().get(`cache:user:${userId}:profile`);
  return cached ? JSON.parse(cached) : null;
}

async function setUserProfile(userId, data) {
  await getClient().set(`cache:user:${userId}:profile`, JSON.stringify(data), 'EX', 300); // 5 min
}

async function invalidateUserProfile(userId) {
  await getClient().del(`cache:user:${userId}:profile`);
}

module.exports = { getReport, setReport, invalidateReport, getUserProfile, setUserProfile, invalidateUserProfile };
