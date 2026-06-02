const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL_NODE,
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
});

pool.on('error', (err) => {
  const logger = require('../services/logger');
  logger.error({ err }, 'Unexpected pg pool error');
});

async function query(text, params) {
  const client = await pool.connect();
  try {
    const result = await client.query(text, params);
    return result;
  } catch (err) {
    throw err;
  } finally {
    client.release();
  }
}

module.exports = { query, pool };
