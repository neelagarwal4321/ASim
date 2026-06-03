const axios = require('axios');

const client = axios.create({
  baseURL: process.env.FASTAPI_INTERNAL_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: { 'X-Internal-Secret': process.env.INTERNAL_API_SECRET || '' },
});

async function startSimulation(payload, apiKey) {
  const headers = apiKey ? { 'X-API-Key': apiKey } : {};
  const { data } = await client.post('/internal/simulate/start', payload, { headers });
  return data;
}

async function getSimulationStatus(simulationId) {
  const { data } = await client.get(`/internal/simulate/${simulationId}/status`);
  return data;
}

async function injectEvent(simulationId, eventPayload, apiKey) {
  const headers = apiKey ? { 'X-API-Key': apiKey } : {};
  const { data } = await client.post(`/internal/simulate/${simulationId}/inject-event`, eventPayload, { headers });
  return data;
}

async function controlSimulation(simulationId, action, apiKey) {
  const headers = apiKey ? { 'X-API-Key': apiKey } : {};
  const { data } = await client.post(`/internal/simulate/${simulationId}/control`, { action }, { headers });
  return data;
}

module.exports = { startSimulation, getSimulationStatus, injectEvent, controlSimulation };
