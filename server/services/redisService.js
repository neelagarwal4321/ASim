const Redis = require('ioredis');

let _pub = null;
let _sub = null;

function getPublisher() {
  if (!_pub) _pub = new Redis(process.env.REDIS_URL);
  return _pub;
}

function getSubscriber() {
  if (!_sub) _sub = new Redis(process.env.REDIS_URL);
  return _sub;
}

module.exports = { getPublisher, getSubscriber };
