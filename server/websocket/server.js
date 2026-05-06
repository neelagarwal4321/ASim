const { WebSocketServer } = require('ws');
const { verify } = require('../services/jwtService');
const { getSubscriber } = require('../services/redisService');
const logger = require('../services/logger');

const subs = new Map(); // simulationId -> Set<ws>

function setupWebSocket(server) {
  const wss = new WebSocketServer({ noServer: true });

  server.on('upgrade', (req, socket, head) => {
    const url = new URL(req.url, `http://${req.headers.host}`);
    const match = url.pathname.match(/^\/ws\/simulate\/([^/]+)$/);
    if (!match) { socket.destroy(); return; }

    const token = url.searchParams.get('token');
    try { verify(token); } catch { socket.write('HTTP/1.1 401 Unauthorized\r\n\r\n'); socket.destroy(); return; }

    wss.handleUpgrade(req, socket, head, (ws) => {
      const simulationId = match[1];
      if (!subs.has(simulationId)) subs.set(simulationId, new Set());
      subs.get(simulationId).add(ws);

      ws.on('message', (data) => {
        try {
          const msg = JSON.parse(data);
          if (msg.type === 'ping') ws.send(JSON.stringify({ type: 'pong' }));
        } catch {}
      });

      ws.on('close', () => {
        const set = subs.get(simulationId);
        if (set) { set.delete(ws); if (!set.size) subs.delete(simulationId); }
      });

      const heartbeat = setInterval(() => {
        if (ws.readyState === ws.OPEN) ws.ping();
      }, 30000);
      ws.on('close', () => clearInterval(heartbeat));

      // Subscribe Redis channel for this simulation
      subscribeIfNeeded(simulationId);
    });
  });
}

const subscribedSims = new Set();

function subscribeIfNeeded(simulationId) {
  if (subscribedSims.has(simulationId)) return;
  subscribedSims.add(simulationId);
  const sub = getSubscriber();
  sub.subscribe(`sim:${simulationId}:rounds`, (err) => {
    if (err) logger.error('Redis subscribe error: %s', err.message);
  });
  sub.on('message', (channel, message) => {
    const id = channel.replace('sim:', '').replace(':rounds', '');
    const clients = subs.get(id);
    if (!clients) return;
    clients.forEach((ws) => {
      if (ws.readyState === ws.OPEN) ws.send(message);
    });
  });
}

module.exports = { setupWebSocket };
