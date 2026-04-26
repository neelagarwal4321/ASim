# ASim Full System Design
**Date:** 2026-04-26  
**Status:** Approved  
**Covers:** All phases — complete backend architecture, every endpoint, full DB schema

---

## 1. Architecture

ASim uses a **dual-backend architecture** with a hard boundary between the two servers.

```
React Frontend (frontend/)
    │
    ├─ HTTPS REST  →  /api/v1/*
    └─ WSS         →  /ws/simulate/:id
                            │
                 ┌──────────▼──────────┐
                 │  Node / Express      │  port 3000  (server/)
                 │  ─────────────────  │
                 │  • JWT + OAuth auth  │
                 │  • REST API gateway  │
                 │  • WebSocket server  │
                 │  • Postgres client   │
                 │  • Redis subscriber  │
                 └──────────┬──────────┘
                            │
              internal HTTP  │  redis ←publish
              localhost:8000 │
                 ┌──────────▼──────────┐
                 │  FastAPI             │  port 8000  (backend/)
                 │  ─────────────────  │
                 │  • Agent generation  │
                 │  • Simulation orch   │
                 │  • LLM executor      │
                 │  • Persuasion engine │
                 │  • Output pipeline   │
                 │  • Celery workers    │
                 └──────────┬──────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
           Ollama       Anthropic   PostgreSQL   MongoDB    Redis
         (local dev)  (production) (relational) (documents) (pub/sub)
```

### Boundary rules (never cross these)
- **Node only:** auth, sessions, user management, REST routes, WebSocket, DB queries (Postgres + Mongo reads), Redis pub/sub subscribe
- **FastAPI only:** agent generation, LLM calls, simulation rounds, persuasion math, output generation, DB writes (Postgres + Mongo), Redis pub/sub publish
- **Communication:** Node → FastAPI via internal HTTP (`FASTAPI_INTERNAL_URL`). FastAPI → Node via Redis channel `sim:{id}:rounds`

---

## 2. Repository Structure

```
asim/
├── CLAUDE.md
├── .env                              # Never committed
├── .env.example
├── docker-compose.yml                # Optional local dev (primary: Supabase + Upstash)
├── docs/
│   ├── ASim_Blueprint.docx
│   ├── ASim_Frontend.docx
│   └── superpowers/specs/            # Design specs (this file)
│
├── server/                           # Node.js + Express (user-facing API)
│   ├── index.js                      # Express app entry point, port 3000
│   ├── package.json
│   ├── routes/
│   │   ├── auth.js                   # /api/v1/auth/*
│   │   ├── simulation.js             # /api/v1/simulate/*
│   │   ├── agents.js                 # /api/v1/simulate/:id/agents/*
│   │   └── events.js                 # /api/v1/simulate/:id/inject-event, /events
│   ├── middleware/
│   │   ├── auth.js                   # JWT verification → req.user
│   │   └── apiKey.js                 # X-API-Key extraction → req.apiKey
│   ├── websocket/
│   │   └── server.js                 # ws upgrade → Redis subscribe → stream to client
│   ├── services/
│   │   ├── simulationService.js      # axios calls to FastAPI /internal/*
│   │   └── redisService.js           # ioredis pub/sub client
│   └── db/
│       └── client.js                 # pg Pool → DATABASE_URL_NODE
│
├── backend/                          # Python + FastAPI (simulation engine)
│   ├── main.py                       # FastAPI entry point, port 8000
│   ├── config.py                     # pydantic-settings env loader
│   ├── requirements.txt
│   ├── cli.py                        # Phase 1 CLI runner
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── models.py                 # AgentProfile, AgentState Pydantic models
│   │   ├── generator.py              # generate_agents(count, seed)
│   │   ├── archetypes.py             # 10 archetype preset definitions
│   │   └── voice_styles.py           # Voice style strings per archetype
│   ├── simulation/
│   │   ├── __init__.py
│   │   ├── orchestrator.py           # Round execution (sequential Phase 1, Celery Phase 2)
│   │   ├── prompt_builder.py         # 6-block prompt assembler
│   │   ├── persuasion_engine.py      # Persuasion formula + 0.15 cap
│   │   ├── action_selector.py        # Trait-weighted action selection
│   │   └── state_manager.py          # AgentState read/write (in-memory Phase 1, DB Phase 2)
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── executor.py               # LLMExecutor — sole LLM interface
│   │   ├── anthropic_provider.py     # Anthropic SDK, cache_control on Blocks 1–3
│   │   ├── ollama_provider.py        # Ollama HTTP client
│   │   └── response_parser.py        # JSON extraction + one retry
│   ├── output/
│   │   ├── __init__.py
│   │   ├── aggregator.py             # Tier 1: verdict (pure Python)
│   │   ├── narrative_synthesizer.py  # Tier 2: narrative LLM call
│   │   ├── counterfactual_prober.py  # Tier 3: what-if probes (Phase 2)
│   │   └── report_assembler.py       # Final report LLM call (Phase 2)
│   ├── graph/                        # Phase 2
│   │   ├── __init__.py
│   │   ├── relationship_graph.py
│   │   └── community_detector.py
│   ├── memory/                       # Phase 2
│   │   ├── __init__.py
│   │   ├── compressor.py
│   │   └── hallucination_checker.py
│   ├── tasks/                        # Phase 2 (Celery)
│   │   ├── __init__.py
│   │   ├── celery_app.py
│   │   ├── round_tasks.py
│   │   └── simulation_tasks.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── health.py                 # GET /health
│   │   └── internal.py               # POST /internal/simulate/start, etc.
│   └── db/
│       ├── __init__.py
│       ├── database.py               # SQLAlchemy async engine + session factory
│       ├── models.py                 # All ORM table definitions
│       └── migrations/               # Alembic migrations
│
└── frontend/                         # React + TypeScript (Phase 3 complete)
    ├── index.html
    ├── vite.config.ts
    ├── tsconfig.json
    ├── package.json
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── store/
        │   ├── simulationStore.ts
        │   ├── authStore.ts
        │   ├── configStore.ts
        │   └── uiStore.ts
        ├── api/
        │   ├── client.ts
        │   ├── simulation.ts
        │   ├── auth.ts
        │   └── websocket.ts
        ├── hooks/
        │   ├── useSimulation.ts
        │   ├── useAuth.ts
        │   ├── useTheme.ts
        │   └── useWebSocket.ts
        ├── lib/
        │   ├── utils.ts
        │   ├── formatters.ts
        │   └── constants.ts
        ├── styles/
        │   ├── globals.css
        │   └── theme.css
        ├── pages/
        │   ├── Landing.tsx
        │   ├── About.tsx
        │   ├── HowItWorks.tsx
        │   ├── Help.tsx
        │   ├── Changelog.tsx
        │   ├── auth/
        │   │   ├── Login.tsx
        │   │   ├── Signup.tsx
        │   │   ├── ForgotPassword.tsx
        │   │   └── ResetPassword.tsx
        │   ├── legal/
        │   │   ├── Terms.tsx
        │   │   └── Privacy.tsx
        │   └── app/
        │       ├── Dashboard.tsx
        │       ├── NewSimulation.tsx
        │       ├── LiveSimulation.tsx
        │       ├── Report.tsx
        │       ├── SimulationHistory.tsx
        │       └── Settings.tsx, ApiKeySettings.tsx, Profile.tsx
        └── components/
            ├── layout/   Navbar, Sidebar, TopBar, Footer, RouteGuard
            ├── landing/  HeroSection, FeatureCards, HowItWorksSteps, UseCaseCards, CTABanner
            ├── simulation/ AgentGlobe, StanceBar, RoundFeed, RoundControls, RoundTimeline, CommunityList, TickerStrip
            ├── report/   VerdictCard, NarrativePanel, SpectrumChart, AgentCard
            └── ui/       ArchetypeBadge, EmotionChip, TraitVector, ConfidenceGauge, HallucinationBanner,
                          ThemeToggle, UserAvatar, ConfirmDialog, LoadingOverlay, EmptyState,
                          ToastNotification, InjectEventModal, AgentDetailDrawer, MetricCard,
                          ActionTag, StatusPill
```

---

## 3. Database Architecture

**Two databases with complementary roles:**

| | PostgreSQL | MongoDB |
|-|-----------|---------|
| **Used for** | Structured relational data | High-volume document data |
| **Access** | SQLAlchemy 2.0 async (Python) + pg (Node) | Motor async (Python) + Mongoose (Node) |
| **Why** | Users, sim configs, agent profiles, relationships, results — ACID, foreign keys matter | Agent states per round, transcripts, LLM responses, community snapshots — high write volume, variable shape |

---

### PostgreSQL Tables

All tables managed by SQLAlchemy 2.0 async ORM + Alembic migrations.

### `users`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| email | TEXT UNIQUE NOT NULL | |
| password_hash | TEXT | null for OAuth-only |
| name | TEXT NOT NULL | |
| avatar_url | TEXT | |
| provider | TEXT | 'local' \| 'google' \| 'github' |
| provider_id | TEXT | OAuth subject ID |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### `simulation_configs`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK→users | |
| scenario | TEXT NOT NULL | |
| mode | TEXT | 'passive' \| 'interactive' |
| agent_count | INT | default 50 |
| rounds | INT | default 5 |
| domain | TEXT | 'general', 'policy', 'crisis', etc. |
| seed | INT | for reproducibility |
| status | TEXT | 'pending'\|'running'\|'paused'\|'complete'\|'failed' |
| created_at | TIMESTAMPTZ | |
| completed_at | TIMESTAMPTZ | null until done |

### `agent_profiles`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| simulation_id | UUID FK→simulation_configs | |
| name | TEXT | |
| archetype | TEXT | |
| trait_vector | JSONB | {openness, conscientiousness, extraversion, agreeableness, neuroticism, moral_rigidity, susceptibility} |
| core_beliefs | TEXT[] | |
| voice_style | TEXT | |
| moral_alignment | TEXT | |
| appeal_type | TEXT | |

### `agent_states`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| agent_id | UUID FK→agent_profiles | |
| simulation_id | UUID FK→simulation_configs | |
| round | INT | |
| stance | FLOAT | [0.0, 1.0] |
| emotion | TEXT | |
| confidence | FLOAT | [0.0, 1.0] |
| memory_text | TEXT | |
| influence_score | FLOAT | |
| last_action | TEXT | |
| last_target | UUID | agent_id, nullable |

### `relationship_edges`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| simulation_id | UUID FK | |
| agent_a_id | UUID FK→agent_profiles | |
| agent_b_id | UUID FK→agent_profiles | |
| trust_score | FLOAT | default 0.5 |
| interaction_count | INT | default 0 |
| betrayal_flag | BOOLEAN | default false |
| UNIQUE | (simulation_id, agent_a_id, agent_b_id) | |

### `round_logs`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| simulation_id | UUID FK | |
| round_number | INT | |
| transcript | JSONB | array of agent action objects |
| stance_distribution | JSONB | {support, oppose, undecided} |
| created_at | TIMESTAMPTZ | |

### `community_snapshots`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| simulation_id | UUID FK | |
| round_number | INT | |
| communities | JSONB | [{id, members[], label}] |
| created_at | TIMESTAMPTZ | |

### `simulation_results`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| simulation_id | UUID FK UNIQUE | |
| verdict | TEXT | dominant outcome |
| confidence | FLOAT | |
| narrative | TEXT | 3–5 sentence arc |
| spectrum | JSONB | counterfactual what-ifs |
| top_agents | JSONB | [{id, name, archetype, influence}] |
| hallucination_level | TEXT | 'green'\|'yellow'\|'red' |
| created_at | TIMESTAMPTZ | |

### `injected_events`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| simulation_id | UUID FK | |
| round_number | INT | injected before this round |
| event_text | TEXT NOT NULL | |
| created_at | TIMESTAMPTZ | |

---

### MongoDB Collections

Motor (Python async) for FastAPI writes. Mongoose (Node) for reads.

#### `agent_states`
Per-agent per-round mutable state. 50 agents × 5 rounds = 250 docs per simulation.

```js
{
  _id: ObjectId,
  simulation_id: "uuid",          // ref to Postgres simulation_configs
  agent_id: "uuid",               // ref to Postgres agent_profiles
  round: 3,
  stance: 0.72,                   // [0.0 oppose → 1.0 support]
  emotion: "angry",
  confidence: 0.65,
  memory_text: "...",             // compressed narrative memory
  influence_score: 0.84,
  last_action: "debate",
  last_target: "uuid",            // agent_id, nullable
  created_at: ISODate
}
// Index: {simulation_id:1, round:1}
// Index: {agent_id:1, round:1}
```

#### `round_logs`
Full verbose transcript of every action taken in a round.

```js
{
  _id: ObjectId,
  simulation_id: "uuid",
  round_number: 3,
  transcript: [
    {
      agent_id: "uuid",
      name: "Alice Chen",
      archetype: "TruthSeeker",
      action: "debate",
      target_id: "uuid",           // nullable
      free_text: "I believe...",
      stance: 0.72,
      emotion: "determined",
      confidence: 0.8
    }
    // ... one entry per agent
  ],
  stance_distribution: {
    support: 0.58,
    oppose: 0.31,
    undecided: 0.11
  },
  created_at: ISODate
}
// Index: {simulation_id:1, round_number:1} unique
```

#### `community_snapshots`
Louvain community detection results per round (Phase 2).

```js
{
  _id: ObjectId,
  simulation_id: "uuid",
  round_number: 3,
  communities: [
    {
      community_id: 0,
      label: "Pro-mandate coalition",
      members: ["uuid", "uuid", ...],
      avg_stance: 0.82,
      dominant_emotion: "optimistic"
    }
  ],
  community_count: 4,
  created_at: ISODate
}
// Index: {simulation_id:1, round_number:1}
```

#### `agent_responses`
Raw LLM responses — audit trail and debugging. Never shown to user.

```js
{
  _id: ObjectId,
  simulation_id: "uuid",
  agent_id: "uuid",
  round: 3,
  prompt_blocks: {
    block1_identity: "...",
    block2_behavioral: "...",
    block3_moral: "...",
    block4_social: "...",
    block5_memory: "...",
    block6_action: "..."
  },
  raw_response: "...",
  parsed_free_text: "...",
  parsed_json: { action: "...", stance: 0.72, emotion: "..." },
  retry_count: 0,               // 0 or 1
  provider: "ollama",           // "ollama" | "anthropic"
  latency_ms: 843,
  created_at: ISODate
}
// Index: {simulation_id:1, agent_id:1, round:1}
// TTL index: expires after 30 days (configurable)
```

#### `memory_logs`
Agent memory compression history (Phase 2).

```js
{
  _id: ObjectId,
  simulation_id: "uuid",
  agent_id: "uuid",
  round: 5,                       // round at which compression ran
  previous_memory: "...",
  new_memory: "...",
  compression_ratio: 0.43,
  created_at: ISODate
}
// Index: {agent_id:1, simulation_id:1}
```

---

## 4. Node/Express API — All Endpoints

Base path: `/api/v1`  
Auth: JWT in httpOnly cookie or `Authorization: Bearer <token>` header

### Auth (`/auth`)

| Method | Path | Auth | Body | Response |
|--------|------|------|------|----------|
| POST | `/auth/register` | — | `{name, email, password}` | `{user, token}` |
| POST | `/auth/login` | — | `{email, password}` | `{user, token}` |
| POST | `/auth/logout` | ✓ | — | `{ok}` |
| POST | `/auth/refresh` | cookie | — | `{token}` |
| GET | `/auth/oauth/google` | — | — | redirect |
| GET | `/auth/oauth/google/callback` | — | — | redirect + set cookie |
| GET | `/auth/oauth/github` | — | — | redirect |
| GET | `/auth/oauth/github/callback` | — | — | redirect + set cookie |
| GET | `/auth/me` | ✓ | — | `{id, name, email, avatarUrl}` |
| PATCH | `/auth/me` | ✓ | `{name?, avatarUrl?}` | `{user}` |
| DELETE | `/auth/me` | ✓ | — | `{ok}` |

### Simulations (`/simulate`)

| Method | Path | Auth | Body / Query | Response |
|--------|------|------|------|----------|
| POST | `/simulate` | ✓ + `X-API-Key` | `{scenario, agentCount, rounds, domain, mode, seed?}` | `{simulationId, status}` |
| GET | `/simulate` | ✓ | `?page&limit&status` | `{items[], total, page}` |
| GET | `/simulate/:id` | ✓ | — | `{SimulationConfig, status, result?}` |
| DELETE | `/simulate/:id` | ✓ | — | `{ok}` |

### Agents

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/simulate/:id/agents` | ✓ | `[AgentProfile]` |
| GET | `/simulate/:id/agents/:agentId` | ✓ | `AgentProfile + AgentState[]` |

### Rounds

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/simulate/:id/rounds` | ✓ | `[{round, stanceDistribution, createdAt}]` |
| GET | `/simulate/:id/rounds/:round` | ✓ | `RoundLog + CommunitySnapshot` |

### Results

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/simulate/:id/result` | ✓ | `SimulationResult` (404 if not complete) |

### Events

| Method | Path | Auth | Body | Response |
|--------|------|------|------|----------|
| POST | `/simulate/:id/inject-event` | ✓ | `{eventText, roundNumber}` | `{ok}` |
| GET | `/simulate/:id/events` | ✓ | — | `[InjectedEvent]` |

### Simulation Control

| Method | Path | Auth | Response |
|--------|------|------|----------|
| POST | `/simulate/:id/pause` | ✓ | `{ok}` |
| POST | `/simulate/:id/resume` | ✓ | `{ok}` |

### Health

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/health` | — | `{status:"ok", uptime, version}` |
| GET | `/health/backend` | — | proxies FastAPI /health |

### WebSocket

```
WSS /ws/simulate/:id
  auth: JWT in ?token= query param or cookie
```

---

## 5. FastAPI Internal API — All Endpoints

Internal only — bound to localhost, never exposed via Nginx/proxy.

| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | `/health` | — | `{status:"ok"}` |
| POST | `/internal/simulate/start` | `{simulation_id, scenario, agent_count, rounds, domain, mode, seed}` | `{ok, simulation_id}` |
| GET | `/internal/simulate/:id/status` | — | `{status, round, agent_count}` |
| POST | `/internal/simulate/:id/inject-event` | `{event_text, round_number}` | `{ok}` |
| POST | `/internal/simulate/:id/pause` | — | `{ok}` |
| POST | `/internal/simulate/:id/resume` | — | `{ok}` |

---

## 6. Redis Protocol

| Key / Channel | Type | TTL | Purpose |
|---------------|------|-----|---------|
| `sim:{id}:rounds` | pub/sub channel | — | FastAPI publishes RoundLog JSON per round; Node subscribes |
| `sim:{id}:status` | string | 24h | Current sim status (running/paused/complete/failed) |
| `sim:{id}:apikey` | string (encrypted) | 24h | AES-256 encrypted user API key; deleted on completion |
| `celery` | queue | — | Celery task broker (Phase 2) |
| `celery-results` | hash | 1h | Celery result backend (Phase 2) |

### API key encryption
```
stored = AES256_encrypt(user_api_key, key=SECRET_KEY)
retrieved = AES256_decrypt(stored, key=SECRET_KEY)
```
Key is deleted from Redis when simulation completes, fails, or after 24h TTL.

---

## 7. WebSocket Message Protocol

**Server → Client messages:**

```jsonc
{"type": "connected",        "simulationId": "uuid"}
{"type": "round_start",      "round": 3}
{"type": "agent_action",     "agentId": "uuid", "name": "Alice",
                              "action": "debate", "message": "...",
                              "stance": 0.72, "emotion": "angry"}
{"type": "round_end",        "round": 3,
                              "stanceDistribution": {"support":0.6,"oppose":0.3,"undecided":0.1},
                              "communityCount": 4}
{"type": "sim_complete",     "result": {"verdict":"...","confidence":0.78,
                                         "narrative":"...","topAgents":[...]}}
{"type": "sim_paused"}
{"type": "sim_resumed"}
{"type": "event_injected",   "eventText": "Breaking news: ..."}
{"type": "error",            "message": "..."}
```

**Client → Server messages:**
```jsonc
{"type": "ping"}
```

---

## 8. Simulation Lifecycle (end-to-end flow)

```
1. User submits POST /simulate with X-API-Key header
2. Node: validate body, create simulation_configs row (status=pending)
3. Node: encrypt API key → Redis sim:{id}:apikey (TTL 24h)
4. Node: POST localhost:8000/internal/simulate/start
5. FastAPI: generate 50 agents → store in agent_profiles (Phase 2) / in-memory (Phase 1)
6. FastAPI: set sim:{id}:status = "running"
7. For each round:
   a. FastAPI: load injected events from injected_events table
   b. FastAPI: action selection per agent
   c. FastAPI: build 6-block prompt per agent
   d. FastAPI: fire LLM calls (sequential Phase 1 / Celery Phase 2)
   e. FastAPI: parse responses, run persuasion engine
   f. FastAPI: update agent_states
   g. FastAPI: update relationship_edges (Phase 2)
   h. FastAPI: run Louvain community detection → community_snapshots (Phase 2)
   i. FastAPI: run memory compression (Phase 2)
   j. FastAPI: run hallucination checker (Phase 2)
   k. FastAPI: write round_logs
   l. FastAPI: publish RoundLog to Redis sim:{id}:rounds
   m. Node: receives Redis message → broadcasts to WebSocket subscribers
8. FastAPI: compute verdict (aggregator)
9. FastAPI: generate narrative (narrative_synthesizer)
10. FastAPI: write simulation_results
11. FastAPI: set sim:{id}:status = "complete", delete sim:{id}:apikey
12. FastAPI: publish {type:"sim_complete"} to Redis
13. Node: receives completion → updates simulation_configs status → sends to client
```

---

## 9. Auth Flow

### Email/Password
```
POST /auth/register → hash password (bcrypt) → insert users row → return JWT
POST /auth/login    → verify password → return JWT in httpOnly cookie + response body
```

### OAuth (Google / GitHub)
```
GET /auth/oauth/google → redirect to Google with client_id + callback URL
GET /auth/oauth/google/callback
  → exchange code for tokens
  → get user profile from Google
  → upsert users row (provider='google', provider_id=sub)
  → set JWT httpOnly cookie → redirect to /app/dashboard
```

### JWT
- Signed with `SECRET_KEY` (HS256)
- Expiry: `JWT_EXPIRY` (default 7d)
- Refresh: `POST /auth/refresh` with valid cookie → new token
- Payload: `{sub: user_id, email, iat, exp}`

---

## 10. Environment Variables (complete list)

```bash
# LLM
LLM_PROVIDER=ollama              # "ollama" | "anthropic"
ANTHROPIC_API_KEY=               # Dev key only — user key comes in X-API-Key header
ANTHROPIC_MODEL=claude-sonnet-4-6
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Database
DATABASE_URL=postgresql+asyncpg://...     # FastAPI (asyncpg driver)
DATABASE_URL_NODE=postgresql://...         # Node (pg driver, same DB)

# Redis
REDIS_URL=redis://...
CELERY_BROKER_URL=redis://.../0
CELERY_RESULT_BACKEND=redis://.../1

# Servers
NODE_PORT=3000
FASTAPI_PORT=8000
FASTAPI_INTERNAL_URL=http://localhost:8000

# Application
APP_ENV=development
SECRET_KEY=                      # 32-char random string — JWT signing + AES key
JWT_EXPIRY=7d

# OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
OAUTH_CALLBACK_BASE=http://localhost:3000  # or production URL
```

---

## 11. Phase Build Order

### Phase 1 (current) — CLI simulation engine
- FastAPI: config, LLM layer, agents, simulation engine, output (verdict + narrative), CLI runner
- No DB, no Celery, sequential execution
- Verification: `python backend/cli.py --scenario "..." --agents 50 --rounds 5`

### Phase 2 — API wiring + DB + parallelism
- FastAPI: DB layer (SQLAlchemy + Alembic), Celery tasks, graph, memory, hallucination checker
- Node: full server scaffold, all routes, auth, WebSocket, Redis pub/sub
- Verification: full API test suite, WebSocket stream test

### Phase 3 (frontend — done)
- All public pages, auth pages, dashboard, NewSimulation, LiveSimulation, Report

### Phase 4 — Integration
- Wire frontend API calls to Node backend
- Wire WebSocket client to Node WebSocket server
- Fill in stub pages: SimulationHistory, Settings, Profile, ApiKeySettings
- End-to-end test: submit scenario → live view → read report

---

## 12. Error Handling

### FastAPI (Python)
- Every LLM call: `try/except` with one automatic retry
- JSON parse failure: retry with stricter prompt once
- Second failure: log `(agent_id, round)`, skip agent, continue sim
- Never `print()` — use Python `logging` module
- Publish `{"type":"error","message":"..."}` to Redis on fatal sim failure

### Node (JavaScript)
- All route handlers wrapped in `try/catch` with central error middleware
- Never return internal error details to client — log + return `500 {error:"internal error"}`
- WebSocket: catch all errors, send `{type:"error",message:"..."}` before closing
- Redis connection errors: log + attempt reconnect, do not crash process

---

## 13. Naming Conventions

| Context | Convention |
|---------|-----------|
| Python files/dirs | snake_case |
| Python classes | PascalCase |
| Python functions/vars | snake_case |
| Python constants | UPPER_SNAKE_CASE |
| JS/TS files (components) | PascalCase |
| JS/TS files (utilities/routes) | camelCase |
| JS/TS variables/functions | camelCase |
| DB tables | snake_case plural |
| DB columns | snake_case |
| REST paths | kebab-case |
| Env vars | UPPER_SNAKE_CASE |
| Redis keys | colon-namespaced `sim:{id}:rounds` |
