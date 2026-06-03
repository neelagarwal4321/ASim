const { WebSocketServer } = require('ws');
const { verify } = require('../services/jwtService');
const { getSubscriber } = require('../services/redisService');
const logger = require('../services/logger');

const ROUND_CHANNEL_RE = /^pubsub:sim:(.+):rounds$/;

const subs = new Map();            // simulationId -> Set<ws>
const subscribedSims = new Set();  // simulationIds with active Redis subscriptions
let messageListenerAttached = false;

const clientCounts = new Map();  // userId -> count
const MAX_CONNECTIONS_PER_USER = 20;

function setupWebSocket(server) {
  const wss = new WebSocketServer({ noServer: true });

  wss.on('error', (err) => logger.error('WSS error: ' + err.message));

  server.on('upgrade', (req, socket, head) => {
    const url = new URL(req.url, `http://${req.headers.host}`);
    const match = url.pathname.match(/^\/ws\/simulate\/([^/]+)$/);
    if (!match) { socket.destroy(); return; }

    const token = url.searchParams.get('token');
    let payload;
    try { payload = verify(token); } catch (e) {
      logger.warn('WS auth failed: ' + e.message);
      socket.write('HTTP/1.1 401 Unauthorized\r\n\r\n'); socket.destroy(); return;
    }

    const userId = payload.userId || 'anon';
    const count = clientCounts.get(userId) || 0;
    if (count >= MAX_CONNECTIONS_PER_USER) {
      logger.warn('WS limit hit user=' + userId + ' count=' + count);
      socket.write('HTTP/1.1 429 Too Many Requests\r\n\r\n');
      socket.destroy();
      return;
    }

    wss.handleUpgrade(req, socket, head, (ws) => {
      // Increment only after successful upgrade so count never leaks
      clientCounts.set(userId, (clientCounts.get(userId) || 0) + 1);
      logger.info('WS connected sim=' + match[1] + ' user=' + userId);
      const simulationId = match[1];
      if (!subs.has(simulationId)) subs.set(simulationId, new Set());
      subs.get(simulationId).add(ws);

      ws.on('message', (data) => {
        try {
          const msg = JSON.parse(data);
          if (msg.type === 'ping') ws.send(JSON.stringify({ type: 'pong' }));
        } catch {}
      });

      const heartbeat = setInterval(() => {
        if (ws.readyState === ws.OPEN) ws.ping();
      }, 30000);

      ws.on('close', () => {
        const c = clientCounts.get(userId) || 1;
        if (c <= 1) clientCounts.delete(userId);
        else clientCounts.set(userId, c - 1);

        const set = subs.get(simulationId);
        if (set) {
          set.delete(ws);
          if (!set.size) {
            subs.delete(simulationId);
            // Remove subscription tracking so the next client can re-subscribe.
            subscribedSims.delete(simulationId);
            const sub = getSubscriber();
            sub.unsubscribe(`pubsub:sim:${simulationId}:rounds`, (err) => {
              if (err) logger.error(`Redis unsubscribe error for sim=${simulationId}: ${err.message}`);
            });
          }
        }
        clearInterval(heartbeat);
      });

      subscribeIfNeeded(simulationId);
    });
  });
}

function subscribeIfNeeded(simulationId) {
  const sub = getSubscriber();
  if (!messageListenerAttached) {
    messageListenerAttached = true;
    sub.on('message', (channel, message) => {
      const match = channel.match(ROUND_CHANNEL_RE);
      if (!match) return;
      const id = match[1];
      const clients = subs.get(id);
      if (!clients) return;
      clients.forEach((ws) => {
        if (ws.readyState === ws.OPEN) ws.send(message);
      });
    });
  }
  if (subscribedSims.has(simulationId)) return;
  subscribedSims.add(simulationId);
  sub.subscribe(`pubsub:sim:${simulationId}:rounds`, (err) => {
    if (err) {
      subscribedSims.delete(simulationId);  // allow retry on next connection
      logger.error(`Redis subscribe error for sim=${simulationId}: ${err.message}`);
      const clients = subs.get(simulationId);
      if (clients) {
        const msg = JSON.stringify({ type: 'error', payload: { code: 'SUBSCRIPTION_FAILED', message: 'Real-time updates unavailable' } });
        clients.forEach((ws) => { if (ws.readyState === ws.OPEN) ws.send(msg); });
      }
    }
  });
}

module.exports = { setupWebSocket };
