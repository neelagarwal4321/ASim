const swaggerJsdoc = require('swagger-jsdoc');

const options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'ASim API',
      version: '1.0.0',
      description: 'Multi-agent AI simulation engine API',
    },
    servers: [{ url: '/api/v1' }],
    components: {
      securitySchemes: {
        BearerAuth: { type: 'http', scheme: 'bearer', bearerFormat: 'JWT' },
        ApiKeyAuth: { type: 'apiKey', in: 'header', name: 'X-API-Key' },
      },
      schemas: {
        Error: {
          type: 'object',
          properties: {
            error: { type: 'string' },
            code: { type: 'string', example: 'RATE_LIMIT_DAILY' },
          },
        },
        PaginationMeta: {
          type: 'object',
          properties: {
            page: { type: 'integer', example: 1 },
            limit: { type: 'integer', example: 20 },
            total: { type: 'integer', example: 142 },
            has_more: { type: 'boolean', example: true },
          },
        },
        SimulationConfig: {
          type: 'object',
          properties: {
            id: { type: 'string', format: 'uuid' },
            scenario: { type: 'string' },
            agent_count: { type: 'integer' },
            rounds: { type: 'integer' },
            status: { type: 'string', enum: ['pending', 'running', 'complete', 'failed', 'cancelled'] },
            estimated_cost: { type: 'number', format: 'float', example: 0.42 },
            created_at: { type: 'string', format: 'date-time' },
          },
        },
        SimulationResult: {
          allOf: [
            { $ref: '#/components/schemas/SimulationConfig' },
            {
              type: 'object',
              properties: {
                verdict: { type: 'string' },
                confidence: { type: 'number' },
                distribution: {
                  type: 'object',
                  properties: {
                    support: { type: 'number' },
                    oppose: { type: 'number' },
                    undecided: { type: 'number' },
                  },
                },
                avg_stance: { type: 'number' },
                narrative: { type: 'string' },
                counterfactuals: { type: 'array', items: { type: 'object' } },
                hallucination_level: { type: 'string', enum: ['green', 'yellow', 'red'] },
              },
            },
          ],
        },
        User: {
          type: 'object',
          properties: {
            id: { type: 'string' },
            email: { type: 'string', format: 'email' },
            display_name: { type: 'string' },
            role: { type: 'string', enum: ['free', 'pro', 'admin'] },
            created_at: { type: 'string', format: 'date-time' },
          },
        },
        AuthTokens: {
          type: 'object',
          properties: {
            accessToken: { type: 'string' },
            refreshToken: { type: 'string' },
            user: { $ref: '#/components/schemas/User' },
          },
        },
      },
    },
    security: [{ BearerAuth: [] }],
  },
  apis: ['./routes/*.js'],
};

module.exports = swaggerJsdoc(options);
