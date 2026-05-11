require('dotenv').config({ path: require('path').join(__dirname, '../.env') });

const http = require('http');
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');

const { setupOAuth } = require('./services/oauthService');
const { setupWebSocket } = require('./websocket/server');
const { errorHandler } = require('./middleware/errorHandler');
const logger = require('./services/logger');

const authRouter = require('./routes/auth');
const simulationRouter = require('./routes/simulation');
const agentsRouter = require('./routes/agents');
const eventsRouter = require('./routes/events');
const usersRouter = require('./routes/users');
const scenariosRouter = require('./routes/scenarios');

const app = express();

// Security + logging
app.use(helmet());
const corsOrigin = process.env.CORS_ORIGIN ||
  (process.env.NODE_ENV !== 'production'
    ? (origin, cb) => cb(null, /^http:\/\/localhost(:\d+)?$/.test(origin || '') ? origin : false)
    : 'http://localhost:5173');
app.use(cors({ origin: corsOrigin, credentials: true }));
app.use(morgan('dev', { stream: { write: (msg) => logger.info(msg.trim()) } }));
app.use(express.json({ limit: '1mb' }));

// OAuth
setupOAuth(app);

// Routes
app.use('/api/v1/auth', authRouter);
app.use('/api/v1/simulate', simulationRouter);
app.use('/api/v1/simulate/:id/agents', agentsRouter);
app.use('/api/v1/simulate/:id', eventsRouter);
app.use('/api/v1/users', usersRouter);
app.use('/api/v1/scenarios', scenariosRouter);

// Health
app.get('/health', (req, res) => res.json({ status: 'ok', service: 'asim-node' }));

// Error handler
app.use(errorHandler);

const PORT = parseInt(process.env.NODE_PORT || '3000');
const server = http.createServer(app);

// WebSocket
setupWebSocket(server);

if (require.main === module) {
  server.listen(PORT, () => {
    logger.info(`ASim Node server listening on port ${PORT}`);
  });

  // Graceful shutdown
  process.on('SIGTERM', () => {
    server.close(() => {
      logger.info('Server closed');
      process.exit(0);
    });
  });
}

module.exports = app;
