# CLAUDE.md — Agent Society Simulator (ASim)

## What Is ASim

ASim is a multi-agent AI simulation engine where hundreds of autonomous agents —
each with a distinct personality, moral alignment, and social behavior — collectively
respond to any scenario, crisis, or question. Agents interact, argue, form communities,
build relationships, manipulate, and produce the most probable real-world outcome for
that scenario through emergent behavior.

The simulation produces three outputs: a dominant outcome verdict, a narrative arc of
how society arrived there, and a spectrum of counterfactual what-ifs.

Full system design is documented in `docs/ASim_Blueprint.docx`. When in doubt about
any architectural decision, read the relevant Blueprint section before writing code.

---

## Dual-Backend Architecture — Critical Rule

ASim uses two separate backend servers with a hard boundary between them.
**No responsibility ever crosses this boundary.**

```
Frontend (React)
      │
      │  REST + WebSocket
      ▼
server/  (Node.js + Express)          ← "dev side" — everything user-facing
  - Auth (JWT, OAuth)
  - REST API routes (POST /simulate, GET /simulate/{id}, etc.)
  - WebSocket server → streams round results to frontend
  - Database read/write (SQLAlchemy via API or direct Postgres calls)
  - Redis pub/sub subscriber
  - X-API-Key extraction + forwarding to backend
  - User management
      │
      │  Internal HTTP (localhost only)
      ▼
backend/  (Python + FastAPI)          ← "agent side" — simulation engine only
  - Agent generation
  - LLM calls (via llm/executor.py)
  - Simulation orchestration
  - Persuasion engine
  - Output pipeline (verdict, narrative)
  - Publishes round results to Redis channel
```

**Node handles:** auth, REST routes, WebSocket, DB queries, Redis pub/sub, OAuth, sessions.
**FastAPI handles:** agents, LLM calls, simulation rounds, persuasion math, output generation.

**Never add to FastAPI:** auth, user management, WebSocket endpoints, frontend-facing routes.
**Never add to Node:** simulation logic, LLM calls, agent generation, persuasion formula.

---

## Session Workflow Rules

### Subagent Strategy
- Use subagents for every multi-file task — keeps main context clean
- Haiku for minimal mechanical tasks (single file, clear spec)
- Sonnet for planning, orchestration, multi-file coordination
- No Opus unless user explicitly requests it
- One task per subagent — focused execution, no shared state

### Verification Before Claiming Done
- Never mark a task complete without running the verification command
- Run `pytest tests/ -q` after every Python change — 46 must always pass
- Run `node -e "require('./server/index')"` after every Node change
- Check `git log --oneline -3` to confirm commit landed

### Plan First
- Enter plan mode for any task with 3+ steps or architectural decisions
- If something goes sideways, stop and re-plan — don't patch over confusion
- Write specs before touching code on new features

### Bug Fixing
- When given a bug report: diagnose root cause first, then fix
- Point at exact file:line before proposing fix
- Never bypass tests or safety checks to make a problem "go away"

### CLAUDE.md Updates
- Update "Current Build State" table after every phase completion
- Add newly discovered rules here, not in lessons.md or other files

---

## Current Build State

| Layer | Status | Notes |
|-------|--------|-------|
| Frontend — public pages, auth, legal | ✅ Complete | Landing, About, HowItWorks, Help, Changelog, Login, Signup, ForgotPassword, ResetPassword, Terms, Privacy |
| Frontend — app shell | ✅ Complete | Sidebar, TopBar, Navbar, Footer, RouteGuard |
| Frontend — Dashboard, NewSimulation | ✅ Complete | |
| Frontend — LiveSimulation, Report | ✅ Complete | Uses mock data; Phase 3 wires to real API |
| Frontend — SimulationHistory, Settings, Profile, ApiKeySettings | 🔲 Stubs | Pages exist but are placeholder shells — Phase 3 |
| Backend Phase 1 — CLI simulation engine | ✅ Complete | 43 tests passing; `python backend/cli.py --scenario "..." --agents 50 --rounds 5` works |
| Backend Phase 2A — FastAPI DB layer | ✅ Complete | SQLAlchemy ORM (9 tables), MongoDB Motor client, Alembic migrations, Celery stubs, Redis publisher, AES-256 API key store, internal REST API |
| Backend Phase 2B — Node/Express API layer | ✅ Complete | JWT + OAuth (Google/GitHub), all REST routes, WebSocket (`/ws/simulate/:id`), Redis pub/sub fan-out |
| Backend Phase 2C — Integration verified | 🔲 Pending | Need real Postgres + Redis running; apply `alembic upgrade head` then smoke test |
| Phase 3 — Frontend wiring | 🔲 Not started | Replace all mock data with real API calls (24 tasks) |

---

## Repo Structure

```
asim/
├── CLAUDE.md                         # This file — read at the start of every session
├── .env                              # Local environment variables — never commit
├── .env.example                      # Committed template of all required env vars
├── docker-compose.yml                # Optional local dev: Redis + Postgres (primary: Supabase + Upstash)
├── docs/
│   ├── ASim_Blueprint.docx           # Full system design reference
│   └── ASim_Frontend.docx            # Frontend architecture and page specs
│
├── server/                           # Node.js + Express — API layer (user-facing)
│   ├── index.js                      # Express app entry point, port 3000
│   ├── package.json                  # express, ws, pg, ioredis, jsonwebtoken, bcrypt, axios
│   ├── routes/
│   │   ├── auth.js                   # /api/v1/auth/* — register, login, logout, OAuth
│   │   ├── simulation.js             # /api/v1/simulate/* — CRUD + pause/resume
│   │   ├── agents.js                 # /api/v1/simulate/:id/agents/*
│   │   └── events.js                 # /api/v1/simulate/:id/inject-event, /events
│   ├── middleware/
│   │   ├── auth.js                   # JWT verification → req.user
│   │   └── apiKey.js                 # X-API-Key extraction → req.apiKey
│   ├── websocket/
│   │   └── server.js                 # ws upgrade → Redis subscribe → stream to client
│   ├── services/
│   │   ├── simulationService.js      # axios → FastAPI /internal/* endpoints
│   │   └── redisService.js           # ioredis pub/sub client
│   └── db/
│       └── client.js                 # pg Pool → DATABASE_URL_NODE
│
├── backend/                          # Python + FastAPI — simulation engine (internal only)
│   ├── main.py                       # FastAPI app entry point
│   ├── config.py                     # All settings loaded from environment
│   ├── requirements.txt
│   │
│   ├── agents/                       # Everything to do with agent identity
│   │   ├── __init__.py
│   │   ├── models.py                 # AgentProfile, AgentState Pydantic models
│   │   ├── generator.py              # Personality generation pipeline
│   │   ├── archetypes.py             # Archetype preset definitions
│   │   └── voice_styles.py           # Voice style string library
│   │
│   ├── simulation/                   # Core simulation engine
│   │   ├── __init__.py
│   │   ├── orchestrator.py           # Round orchestrator — coordinates all components
│   │   ├── prompt_builder.py         # Assembles 6-block agent prompt each round
│   │   ├── persuasion_engine.py      # Persuasion resolution formula
│   │   ├── action_selector.py        # Per-agent action selection logic
│   │   └── state_manager.py          # Reads/writes AgentState, RelationshipEdge
│   │
│   ├── graph/                        # Relationship and community graph
│   │   ├── __init__.py
│   │   ├── relationship_graph.py     # NetworkX graph, trust score updates
│   │   └── community_detector.py     # Louvain algorithm, community snapshots
│   │
│   ├── memory/                       # Agent memory management
│   │   ├── __init__.py
│   │   ├── compressor.py             # Narrative memory compression
│   │   └── hallucination_checker.py  # Consistency validation, warning flags
│   │
│   ├── llm/                          # LLM abstraction layer — provider-agnostic
│   │   ├── __init__.py
│   │   ├── executor.py               # Main LLM call interface used by all components
│   │   ├── anthropic_provider.py     # Anthropic SDK implementation
│   │   ├── ollama_provider.py        # Ollama implementation (local testing only)
│   │   └── response_parser.py        # Extracts JSON block from LLM response
│   │
│   ├── output/                       # Output layer — verdict, narrative, spectrum
│   │   ├── __init__.py
│   │   ├── aggregator.py             # Tier 1: statistical verdict computation
│   │   ├── narrative_synthesizer.py  # Tier 2: narrative arc LLM call
│   │   ├── counterfactual_prober.py  # Tier 3: what-if probes
│   │   └── report_assembler.py       # Final unified report LLM call
│   │
│   ├── tasks/                        # Celery async tasks
│   │   ├── __init__.py
│   │   ├── celery_app.py             # Celery app instance and config
│   │   ├── round_tasks.py            # Per-agent LLM call tasks (parallelized)
│   │   └── simulation_tasks.py       # Full simulation lifecycle tasks
│   │
│   ├── api/                          # FastAPI internal route handlers (not exposed to internet)
│   │   ├── __init__.py
│   │   ├── internal.py               # POST /internal/simulate/start, /internal/simulate/{id}/status
│   │   └── health.py                 # GET /health — liveness check
│   │
│   └── db/                           # Database layer
│       ├── __init__.py
│       ├── database.py               # SQLAlchemy async engine, Postgres session factory
│       ├── models.py                 # All SQLAlchemy ORM table definitions (Postgres)
│       ├── mongo.py                  # Motor async client, MongoDB collections
│       └── migrations/               # Alembic migration files (Postgres only)
│
└── frontend/
    ├── index.html
    ├── vite.config.ts            # Tailwind v4 loaded via @tailwindcss/vite plugin — no tailwind.config.ts needed
    ├── tsconfig.json
    ├── package.json
    │
    └── src/
        ├── main.tsx
        ├── App.tsx                   # Router setup, theme provider, auth guard
        │
        ├── store/                    # Zustand state management
        │   ├── simulationStore.ts    # Live simulation state
        │   ├── authStore.ts          # Auth state, user object
        │   ├── configStore.ts        # User config and API key
        │   └── uiStore.ts            # Sidebar collapsed, theme, toasts
        │
        ├── api/                      # Frontend API client
        │   ├── client.ts             # Axios instance with base URL + auth header
        │   ├── simulation.ts         # Simulation API calls
        │   ├── auth.ts               # Login, signup, OAuth, reset password
        │   └── websocket.ts          # WebSocket connection manager
        │
        ├── hooks/                    # Custom React hooks
        │   ├── useSimulation.ts      # Simulation state and controls
        │   ├── useAuth.ts            # Auth state and actions
        │   ├── useTheme.ts           # Theme toggle and persistence
        │   └── useWebSocket.ts       # WebSocket lifecycle management
        │
        ├── lib/                      # Utilities
        │   ├── utils.ts              # General helpers
        │   ├── formatters.ts         # Date, number, stance formatters
        │   └── constants.ts          # Archetype colors, action types, routes
        │
        ├── styles/                   # Global styles
        │   ├── globals.css           # Tailwind base + global resets
        │   └── theme.css             # CSS custom properties for both themes
        │
        ├── pages/
        │   ├── Landing.tsx           # Marketing homepage
        │   ├── About.tsx             # About page
        │   ├── HowItWorks.tsx        # Step-by-step explainer
        │   ├── Help.tsx              # Help and documentation
        │   ├── Changelog.tsx         # Version history
        │   ├── auth/
        │   │   ├── Login.tsx         # Login — OAuth + email/password
        │   │   ├── Signup.tsx        # Signup — OAuth + email/password
        │   │   ├── ForgotPassword.tsx
        │   │   └── ResetPassword.tsx
        │   ├── legal/
        │   │   ├── Terms.tsx         # Terms and conditions
        │   │   └── Privacy.tsx       # Privacy policy
        │   └── app/                  # Authenticated app pages
        │       ├── Dashboard.tsx     # User home after login
        │       ├── NewSimulation.tsx  # Scenario input + config + launch
        │       ├── LiveSimulation.tsx # Real-time theater view
        │       ├── Report.tsx        # Sealed read-only final report
        │       ├── SimulationHistory.tsx # Archive of all past simulations
        │       ├── Settings.tsx      # Account, appearance, notifications
        │       ├── ApiKeySettings.tsx # API key management
        │       └── Profile.tsx       # Display name, avatar, account details
        │
        └── components/
            ├── layout/               # App shell components
            │   ├── Navbar.tsx        # Public top navbar
            │   ├── Sidebar.tsx       # App left sidebar (collapsible)
            │   ├── TopBar.tsx        # App top bar with breadcrumb + avatar
            │   ├── Footer.tsx        # Public footer with links
            │   └── RouteGuard.tsx    # Auth protection wrapper
            ├── landing/              # Landing page sections
            │   ├── HeroSection.tsx   # WebGL particle network + headline
            │   ├── FeatureCards.tsx  # Three feature cards with icons
            │   ├── HowItWorksSteps.tsx # Step timeline section
            │   ├── UseCaseCards.tsx  # Policy, crisis, ethics cards
            │   └── CTABanner.tsx     # Final CTA section
            ├── simulation/           # Live simulation components
            │   ├── AgentGlobe.tsx    # Three.js 3D agent globe (social graph)
            │   ├── StanceBar.tsx     # Animated stance distribution bar
            │   ├── RoundFeed.tsx     # Live agent message feed
            │   ├── RoundControls.tsx # Pause, inject, add/remove agent
            │   ├── RoundTimeline.tsx # Round progress indicator
            │   ├── CommunityList.tsx # Detected community list display
            │   └── TickerStrip.tsx   # Scrolling event ticker
            ├── report/               # Final report components
            │   ├── VerdictCard.tsx   # Dominant outcome + confidence
            │   ├── NarrativePanel.tsx # Editorial narrative arc
            │   ├── SpectrumChart.tsx  # Counterfactual probe results
            │   └── AgentCard.tsx     # Influential agent profile card
            └── ui/                   # Shared UI components
                ├── ArchetypeBadge.tsx
                ├── EmotionChip.tsx
                ├── TraitVector.tsx
                ├── ConfidenceGauge.tsx
                ├── HallucinationBanner.tsx
                ├── ThemeToggle.tsx
                ├── UserAvatar.tsx
                ├── ConfirmDialog.tsx
                ├── LoadingOverlay.tsx
                ├── EmptyState.tsx
                ├── ToastNotification.tsx
                ├── InjectEventModal.tsx
                ├── AgentDetailDrawer.tsx
                ├── MetricCard.tsx    # Summary stat card
                ├── ActionTag.tsx     # Action type tag/badge
                └── StatusPill.tsx    # Status indicator pill

```

---

## Environment Variables

All configuration lives in `.env`. Never hardcode any value. The full list of
required variables is in `.env.example`. Key variables:

```
# LLM Provider — switch between local testing and production
LLM_PROVIDER=ollama              # "ollama" for local testing, "anthropic" for production

# Anthropic (production) — populated by user at runtime, not stored server-side
# In production, the user's API key is passed per-request in the request header
# ANTHROPIC_API_KEY is only used for your own dev/test runs

ANTHROPIC_API_KEY=               # Your personal dev key — never commit
ANTHROPIC_MODEL=claude-sonnet-4-6

# Ollama (local testing)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/asim   # FastAPI
DATABASE_URL_NODE=postgresql://user:password@localhost:5432/asim       # Node

# MongoDB
MONGODB_URL=mongodb+srv://user:password@cluster.mongodb.net/asim       # Atlas or local
MONGODB_DB=asim

# Redis
REDIS_URL=redis://localhost:6379

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Application
APP_ENV=development              # "development" or "production"
SECRET_KEY=                      # 32-char random string — JWT signing + AES-256 API key encryption
JWT_EXPIRY=7d

# Server ports
NODE_PORT=3000
FASTAPI_PORT=8000
FASTAPI_INTERNAL_URL=http://localhost:8000

# OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
OAUTH_CALLBACK_BASE=http://localhost:3000
```

---

Read CLAUDE.md and docs/ASim_Blueprint.docx before doing anything.
Use the backend-builder skill for this session.
You are running on Sonnet 4.6 — be precise and literal. 
Follow the specifications exactly as written. 
Do not infer or improvise architectural decisions.
If something is unclear, state the ambiguity before proceeding.
Active Python venv is at .venv/ — all pip installs use this venv.
LLM_PROVIDER=ollama for all code in this session.

Then build the following

## Backend Prerequisites

Before starting any backend session, verify all of these are in place:

- Python 3.11+ installed — verify with `python --version`
- Virtual environment at `.venv/` — activate before every session:
  Windows: `.venv\Scripts\activate`
  Mac/Linux: `source .venv/bin/activate`
- If you see "module not found" errors, the venv is not active — activate it first
- Ollama installed and running locally on port 11434
  Pull the model: `ollama pull llama3.1:8b`
  Verify: `ollama run llama3.1:8b "say hello"`
- Supabase project created — connection string in `.env` DATABASE_URL
- Upstash Redis created — URL in `.env` REDIS_URL
- All secrets in `.env` — never committed to git
- `LLM_PROVIDER=ollama` for all development and testing
- `LLM_PROVIDER=anthropic` only for production deployment
- Never run backend commands without activating venv first

### Backend Session Preamble (use this every session)

```
Read CLAUDE.md and docs/ASim_Blueprint.docx before doing anything.
Use the backend-builder skill for this session.
You are running on Sonnet 4.6 — be precise and literal.
Follow specifications exactly as written.
Do not infer or improvise architectural decisions.
If something is unclear, state the ambiguity before proceeding.
Active Python venv is at .venv/ — all pip installs use this venv.
LLM_PROVIDER=ollama for all code in this session.
```


## LLM Abstraction Layer — Critical Pattern

**This is the most important architectural rule in the entire codebase.**

Every single LLM call in the entire backend MUST go through `llm/executor.py`.
No component ever imports the Anthropic SDK or calls Ollama directly.
The executor is the only place that knows which provider is active.

```python
# CORRECT — every component does this
from llm.executor import llm_executor
response = await llm_executor.complete(prompt, system=system_prompt)

# WRONG — never do this anywhere outside llm/
import anthropic
client = anthropic.Anthropic()
```

The executor reads `LLM_PROVIDER` from config and routes to the correct provider.
Switching from Ollama to Anthropic is one environment variable change — nothing else.

### Prompt Caching (Anthropic provider only)

The Anthropic provider MUST implement prompt caching on all agent system prompts.
Blocks 1, 2, and 3 of the agent prompt (identity, behavioral instructions, moral
framing) are static per agent per simulation. Mark them with `cache_control` in
the Anthropic SDK. This reduces user API costs by 60-70% per simulation.
See Anthropic SDK docs for `cache_control` implementation.

### Why the 6-Block Order Is Architectural, Not Arbitrary

The 6 blocks must always appear in this exact sequence: Identity → Behavioral
→ Moral → Social Context → Memory → Action Instruction. This order is
load-bearing and encodes a theory of how personality actually works.

Blocks 1–3 establish who the agent IS before they know anything about the
current situation. Identity, behavioral style, and moral framework exist
independently of any specific event. If Block 4 (social context) comes before
Block 1, the agent forms their identity around their community rather than the
other way around — every agent becomes a conformist and personality
differentiation collapses.

Block 4 gives social reality AFTER identity is established, so social pressure
modifies a person rather than defines them from scratch.

Block 5 gives history and emotional state AFTER social context, so the agent
knows where they stand before being asked to act.

Block 6 gives the specific task last — act now, in this way, toward this
target — after everything else is loaded.

Never reorder these blocks. Never merge blocks. Never skip a block even if its
content is minimal for a given agent.

### User API Key Handling

In production, users provide their own Anthropic API key. The key is:
- Sent by the frontend in the `X-API-Key` request header
- Extracted by the API layer and passed to the LLM executor per-request
- NEVER stored in the database or logged anywhere
- Only lives in memory for the duration of the request/simulation

---

## Database Rules

ASim uses **two databases**:
- **PostgreSQL** — structured relational data (ACID, foreign keys)
- **MongoDB** — high-volume document data (per-round logs, LLM responses)

### PostgreSQL (SQLAlchemy 2.0 async + Alembic)
- Never write raw SQL — SQLAlchemy ORM only
- All DB access through `db/database.py` session factory
- All table definitions in `db/models.py` — never elsewhere
- Schema changes via Alembic migrations — never alter manually
- Node reads Postgres directly via `pg` driver (`DATABASE_URL_NODE`)

**Core Postgres tables:**
- `users` — auth, accounts, OAuth provider info
- `simulation_configs` — scenario, mode, agent count, rounds, domain, seed, status
- `agent_profiles` — fixed identity: archetype, trait_vector, core_beliefs, voice_style
- `relationship_edges` — trust scores, interaction counts, betrayal flags
- `simulation_results` — final verdict, narrative, spectrum, top_agents, hallucination_level
- `injected_events` — user-injected mid-simulation events

### MongoDB (Motor async — Python, Mongoose — Node)
- All MongoDB access through `db/mongo.py` in FastAPI (Phase 2)
- Never raw dict inserts — always use typed Pydantic models before writing

**Core MongoDB collections:**
- `agent_states` — per-agent per-round mutable state (stance, emotion, memory_text)
- `round_logs` — full verbose round transcripts with all agent actions
- `community_snapshots` — Louvain community detection results per round
- `agent_responses` — raw LLM prompt + response pairs (audit, debugging)
- `memory_logs` — agent memory compression history

**Why the split:** PostgreSQL handles data that needs relational integrity (who owns what simulation, which agents belong to which sim). MongoDB handles the write-heavy per-round data that grows as O(agents × rounds) and has variable shapes (transcripts, communities).

---

## Simulation Engine Rules

### Round Execution Order

The orchestrator MUST execute each round in this exact sequence. Do not reorder.

1. Load scenario + any injected events for this round
2. Each agent forms independent prior (no social context yet)
3. Action selection per agent (weighted by trait vector)
4. Build full 6-block prompt per agent
5. Fire all agent LLM calls in parallel via Celery tasks
6. Parse all responses — extract free text + JSON block
7. Run persuasion resolution engine on all interaction pairs
8. Update AgentState records for this round
9. Update RelationshipEdge records
10. Run Louvain community detection → write CommunitySnapshot
11. Run memory compression for agents above threshold
12. Run hallucination checker → update warning level
13. Write RoundLog
14. Emit round state to WebSocket (if interactive mode)

### The 6-Block Prompt Structure

Every agent prompt is assembled from exactly 6 blocks in this order:
Block 1: Identity (fixed — from AgentProfile)
Block 2: Behavioral instructions (fixed — derived from trait vector at profile creation)
Block 3: Moral framing (fixed — from AgentProfile)
Block 4: Social context (dynamic — current trust scores, community, leader)
Block 5: Round memory (dynamic — compressed narrative + current stance + emotion)
Block 6: Action instruction (dynamic — action type, target, JSON output spec)

The JSON output block at the end of Block 6 is non-negotiable and must always be
present. The response parser relies on it. If it's missing, retry the call once
with a stricter prompt before failing.

### Persuasion Formula

```
persuasion_score =
    trust_score(A→B)          * 0.30
  + argument_quality(A)       * 0.25
  + emotional_resonance(A, B) * 0.20
  + social_proof(A)           * 0.15
  + repetition_bonus          * 0.10

if persuasion_score > B.susceptibility_threshold:
    delta = persuasion_score * (1 - B.moral_rigidity) * 0.2
    B.stance += delta  # clamped to [0.0, 1.0]
```

Hard rules:
- Max stance delta per round: 0.15 (clamp it — prevents runaway consensus)
- Moral rigidity of 0.9+ means max delta of 0.02 regardless of persuasion score
- Emotional resonance is 0 if A's appeal type doesn't match B's current emotion

---

## Output Pipeline Architecture — Why It Is Not a Task Agent System

The output generation pipeline (Tier 1 verdict → Tier 2 narrative → Tier 3
counterfactuals → report assembly) is a straight sequential function chain.
It is NOT a task agent system and must never be built as one.

A task agent system is appropriate when the path to the output is unknown —
the agent decides what to do next based on what it just found. ASim's output
pipeline is the opposite: every step is predetermined, sequential, and
deterministic. No step needs to decide what the next step is.

The correct implementation is four function calls in sequence:
  1. aggregator.compute_verdict()         ← pure Python, no LLM
  2. narrative_synthesizer.generate()     ← one LLM call, one output
  3. counterfactual_prober.run_probes()   ← pure Python + small LLM calls
  4. report_assembler.assemble()          ← one LLM call, one output

Do not introduce LangGraph, LangChain, or any agent orchestration framework
into the output layer. The pipeline is simple enough that doing so adds
abstraction overhead with zero benefit and makes debugging significantly
harder.

---

## API Design Rules

### Node/Express (server/) — user-facing layer
- All routes follow REST conventions
- Auth via JWT middleware on all protected routes
- `X-API-Key` header extracted by `middleware/apiKey.js` and forwarded to FastAPI
- WebSocket server at `/ws/simulate/:id` — subscribes to Redis channel, streams JSON to client
- Never return internal error details to the client — log them, return generic message
- All simulation endpoints require a simulation ID in the path after creation
- Use `express-validator` for request validation — never trust raw body fields

### FastAPI (backend/) — internal simulation engine
- Internal-only endpoints under `/internal/*` — never exposed to internet
- All request/response bodies use Pydantic models — never raw dicts
- All endpoints are async
- Publishes `RoundLog` JSON to Redis channel `sim:{id}:rounds` after each round
- No auth on FastAPI — security enforced at the Node layer

---

## Frontend Rules

- Language: TypeScript everywhere — no `.js` files in `src/`
- All API calls go through `api/client.ts` — never use fetch directly in components
- All simulation state lives in Zustand stores — never in component local state
  unless it's purely UI state (hover, open/closed, etc.)
- The user's API key lives in `configStore` and is sent as a header on every request
- Three.js (AgentGlobe.tsx) is used for the live simulation 3D agent globe — do not
  use React Flow or D3 for the simulation view
- Recharts is used exclusively for all charts — do not mix chart libraries
- shadcn/ui components for all UI elements — do not introduce other component libraries
- Tailwind for all styling — no CSS modules, no styled-components
- Framer Motion for all animations — no CSS transitions on interactive elements,
  no other animation library
- Three.js for: (1) landing page hero WebGL particle network (HeroSection.tsx),
  (2) live simulation 3D agent globe (AgentGlobe.tsx) — no other Three.js usage
- Aurora borealis inspired color system — teal, cyan, viridian, mild blue, 
  purple, dark gradient. Full token system in ASim_Frontend.docx Section 01.
  Both dark mode (default) and light mode fully specified. Never hardcode 
  colors — always use CSS custom property tokens.

### Page Structure

All pages are defined in `docs/ASim_Frontend.docx` Section 02 and Section 06.
The complete route table is in Section 06. Do not add pages or routes beyond
what is listed in that document without explicit instruction.

Frontend is built in two phases:
- Phase 3 (first frontend build): public pages + auth + dashboard + simulate/new
- Phase 4: live simulation page + report page + remaining app pages

---

## Phase 1 MVP Scope — What to Build First

Phase 1 is a working end-to-end simulation loop. Nothing more.

**In scope:**
- Personality generation pipeline (50 agents, mix of archetypes + random)
- Prompt builder (all 6 blocks)
- LLM executor with Ollama provider (Anthropic provider stubbed)
- Response parser with JSON extraction + one retry on failure
- Persuasion engine (full formula)
- State manager (in-memory only — no DB yet)
- Sequential round orchestrator (no Celery yet — one agent at a time)
- Output aggregator (Tier 1 verdict only)
- Narrative synthesizer (Tier 2 — single LLM call)
- CLI runner: `python backend/cli.py --scenario "..." --agents 50 --rounds 5`
- Prints verdict + narrative to terminal

**Explicitly out of scope for Phase 1:**
- Database (use in-memory dicts)
- Celery / parallel execution
- Community detection
- Memory compression
- Hallucination checker
- Counterfactual probes
- WebSocket / real-time
- Frontend
- User API key handling
- Deployment

When Phase 1 is working and produces interesting emergent output, move to Phase 2.
Do not add Phase 2 components during Phase 1 sessions.

---

## What "Done" Means for Phase 1

A single command:
```bash
python backend/cli.py --scenario "A government mandates vaccines for all citizens" \
                      --agents 50 \
                      --rounds 5
```

Produces terminal output containing:
- A dominant outcome with percentage
- The top 3 influential agents
- A 3-5 sentence narrative arc

If this works and the agents feel like different people, Phase 1 is done.

---

## Error Handling Rules

- Every LLM call is wrapped in try/except with one automatic retry
- JSON parse failures: retry once with a stricter prompt that says
  "Your previous response was missing the required JSON block. Respond again
  and end with the JSON block exactly as specified."
- If retry also fails: log the agent ID and round, skip this agent for this round,
  do not crash the simulation
- Database errors: always log with full traceback, never swallow silently
- WebSocket disconnects: clean up the connection, do not crash the simulation

---

## Naming Conventions

- Python files and folders: `snake_case`
- Python classes: `PascalCase`
- Python functions and variables: `snake_case`
- Python constants: `UPPER_SNAKE_CASE`
- TypeScript files: `PascalCase` for components, `camelCase` for utilities
- TypeScript types/interfaces: `PascalCase`
- TypeScript variables and functions: `camelCase`
- Database table names: `snake_case` plural (e.g. `agent_profiles`)
- Database column names: `snake_case`
- API route paths: `kebab-case` (e.g. `/simulate/{id}/inject-event`)
- Environment variables: `UPPER_SNAKE_CASE`

---

## What Claude Code Should Never Do

- Never install a new dependency without checking if an existing one already covers it
- Never store the user's API key in the database or log it anywhere
- Never write raw SQL — use SQLAlchemy ORM (Python) or parameterized queries (Node)
- Never add auth, sessions, or WebSocket endpoints to FastAPI (backend/) — those belong in Node (server/)
- Never add simulation logic, LLM calls, or agent code to Node (server/) — those belong in FastAPI (backend/)
- Never call the Anthropic SDK or Ollama directly outside of `llm/`
- Never add frontend pages or routes beyond what is defined in
  docs/ASim_Frontend.docx without explicit instruction
- Never use `print()` for logging in backend — use Python's `logging` module
- Never commit `.env` — it is in `.gitignore`
- Never skip the JSON block in the agent prompt — the parser depends on it
- Never reorder the 6 prompt blocks — the structure is load-bearing
- Never exceed the max stance delta of 0.15 per round — enforce it in the engine
- Never run Phase 2 components during a Phase 1 session
- Never suggest or introduce LangChain or LangGraph anywhere in the codebase.
  ASim's simulation loop is a social emergence system, not a task pipeline.
  LangGraph's workflow graph is incompatible with ASim's relationship graph
  model. The Anthropic SDK direct is the only LLM interface used.
- Never restructure the output pipeline (aggregator → narrative → counterfactual
  → assembler) into an agent-based system. It is a sequential function chain
  by design.
- Never place Block 4, 5, or 6 content before Block 1, 2, or 3 in any agent
  prompt. The identity-first ordering is architecturally required.

---

## Key Reference: Blueprint Sections

When building specific components, read the corresponding Blueprint section first:

| Component | Blueprint Section |
|---|---|
| Agent personality, traits, archetypes | Section 02 |
| Round structure, action types, persuasion formula | Section 03 |
| Relationship graph, community detection | Section 04 |
| 6-block prompt, voice styles, memory compression | Section 05 |
| Passive vs interactive mode, config params | Section 06 |
| Verdict, narrative, counterfactuals, report assembly | Section 07 |
| All data entities and round data flow | Section 08 |
| All system components and their responsibilities | Section 09 |
| What is and isn't needed to build | Section 10 |
| Phase build plan | Section 11 |
| Frontend pages, components, routes, design system | ASim_Frontend.docx — All Sections |
