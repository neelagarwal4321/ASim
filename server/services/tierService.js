const { query } = require('../db/client');
const { getClient } = require('./redisService');

// Module-level defaults — O(1) lookup by role key
const TIER_DEFAULTS = {
  free:  { max_agents: 50,  max_rounds: 10,  max_daily_sims: 10,  max_concurrent: 1,  max_duration_seconds: 1800 },
  pro:   { max_agents: 200, max_rounds: 50,  max_daily_sims: 100, max_concurrent: 3,  max_duration_seconds: 7200 },
  admin: { max_agents: 500, max_rounds: 200, max_daily_sims: 9999, max_concurrent: 99, max_duration_seconds: 7200 },
};

const CACHE_KEY = 'cache:tier_config';
const CACHE_TTL_SECONDS = 300;

async function getTierLimits(role) {
  const redis = getClient();
  const cached = await redis.get(CACHE_KEY);
  if (cached) {
    const config = JSON.parse(cached);
    return config[role] || TIER_DEFAULTS[role] || TIER_DEFAULTS.free;
  }
  try {
    const { rows } = await query('SELECT * FROM tier_config');
    if (rows.length) {
      const config = Object.fromEntries(rows.map(r => [r.role, r]));
      await redis.set(CACHE_KEY, JSON.stringify(config), 'EX', CACHE_TTL_SECONDS);
      return config[role] || TIER_DEFAULTS[role] || TIER_DEFAULTS.free;
    }
  } catch (_) { /* DB unavailable — fall through */ }
  return TIER_DEFAULTS[role] || TIER_DEFAULTS.free;
}

function getMidnightUTC() {
  const now = new Date();
  return Math.floor(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1) / 1000);
}

async function checkAndIncrementDaily(userId, role) {
  const limits = await getTierLimits(role);
  if (limits.max_daily_sims >= 9999) return { ok: true, limits };
  const redis = getClient();
  const key = `ratelimit:sim:daily:${userId}`;
  const count = await redis.incr(key);
  if (count === 1) await redis.expireat(key, getMidnightUTC());
  if (count > limits.max_daily_sims) {
    await redis.decr(key);
    return { ok: false, code: 'RATE_LIMIT_DAILY', limits, reset: getMidnightUTC() };
  }
  return { ok: true, limits, remaining: limits.max_daily_sims - count, reset: getMidnightUTC() };
}

async function checkAndIncrementActive(userId, limits) {
  if (limits.max_concurrent >= 99) return { ok: true };
  const redis = getClient();
  const key = `ratelimit:sim:active:${userId}`;
  const count = await redis.incr(key);
  await redis.expire(key, limits.max_duration_seconds);
  if (count > limits.max_concurrent) {
    await redis.decr(key);
    return { ok: false, code: 'RATE_LIMIT_CONCURRENT' };
  }
  return { ok: true };
}

module.exports = { getTierLimits, checkAndIncrementDaily, checkAndIncrementActive };
