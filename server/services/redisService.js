const Redis = require('ioredis');

const REDIS_OPTIONS = {
  retryStrategy: (times) => Math.min(times * 100, 3000), // exponential backoff, max 3s
  maxRetriesPerRequest: 3,
  enableOfflineQueue: true,
  lazyConnect: false,
};

function createClient() {
  const client = new Redis(process.env.REDIS_URL, REDIS_OPTIONS);
  client.on('error', (err) => {
    const logger = require('./logger');
    logger.error({ err }, 'Redis connection error');
  });
  client.on('connect', () => {
    const logger = require('./logger');
    logger.info('Redis connected');
  });
  return client;
}

let _pub = null;
let _sub = null;
let _client = null;

function getPublisher() {
  if (!_pub) _pub = createClient();
  return _pub;
}

function getSubscriber() {
  if (!_sub) _sub = createClient();
  return _sub;
}

function getClient() {
  if (!_client) _client = createClient();
  return _client;
}

module.exports = { getPublisher, getSubscriber, getClient };
