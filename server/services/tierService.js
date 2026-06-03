const { query } = require('../db/client');
const { getClient } = require('./redisService');

// Atomic: INCR and set expiry in one script
const LUA_INCR_EXPIRE = `
  local count = redis.call('INCR', KEYS[1])
  if count == 1 then
    redis.call('EXPIREAT', KEYS[1], ARGV[1])
  end
  return count
`;

// Module-level defaults — O(1) lookup by role key
const TIER_DEFAULTS = {
  free:  { max_agents: 50,  max_rounds: 10,  max_daily_sims: 10,  max_concurrent: 1,  max_duration_seconds: 1800 },
  pro:   { max_agents: 200, max_rounds: 50,  max_daily_sims: 100, max_concurrent: 3,  max_duration_seconds: 7200 },
  admin: { max_agents: 500, max_rounds: 200, max_daily_sims: 9999, max_concurrent: 99, max_duration_seconds: 7200 },
};

const CACHE_KEY = 'cache:tier_config';
const CACHE_TTL_SECONDS = 300;

async function getTierLimits(role) {
  const redisClient = getClient();
  const cached = await redisClient.get(CACHE_KEY);
  if (cached) {
    const config = JSON.parse(cached);
    return config[role] || TIER_DEFAULTS[role] || TIER_DEFAULTS.free;
  }
  try {
    const { rows } = await query('SELECT * FROM tier_config');
    if (rows.length) {
      const config = Object.fromEntries(rows.map(r => [r.role, r]));
      await redisClient.set(CACHE_KEY, JSON.stringify(config), 'EX', CACHE_TTL_SECONDS);
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
  const redisClient = getClient();
  const key = `ratelimit:sim:daily:${userId}`;
  const midnight = getMidnightUTC();
  const count = await redisClient.eval(LUA_INCR_EXPIRE, 1, key, midnight);
  if (count > limits.max_daily_sims) {
    await redisClient.decr(key);
    return { ok: false, code: 'RATE_LIMIT_DAILY', limits, reset: midnight };
  }
  return { ok: true, limits, remaining: limits.max_daily_sims - count, reset: midnight };
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

async function decrementActive(userId) {
  const redis = getClient();
  const key = `ratelimit:sim:active:${userId}`;
  const val = await redis.decr(key);
  if (val <= 0) await redis.del(key);
}

module.exports = { getTierLimits, checkAndIncrementDaily, checkAndIncrementActive, decrementActive };
