# ASim — Multi-Agent AI Simulation Engine

Simulate hundreds of personality-distinct AI agents reacting to a scenario through emergent persuasion, trust dynamics, and community formation. Output: verdict, narrative, and a counterfactual spectrum.

## What It Does

Drop a scenario (e.g., "Should this city ban cars?"). ASim spins up configurable agent populations — each with unique traits, moral frameworks, and susceptibility profiles — runs multi-round deliberation, models persuasion and social influence, detects emergent communities, and delivers a structured report with verdict + counterfactual analysis.

## Architecture

Frontend (React + TypeScript + Vite + Tailwind v4 + Three.js)
│  REST + WebSocket
▼
server/  (Node.js + Express)       — auth, sessions, WebSocket fanout
│  Internal HTTP
▼
backend/  (Python + FastAPI)       — simulation engine, LLM calls, agents



- **Node layer:** JWT auth, Google/GitHub OAuth, WebSocket pub/sub via Redis
- **FastAPI layer:** Agent orchestration, LLM execution, persuasion engine, output pipeline
- **Postgres:** Users, simulation configs, agent profiles, relationship edges, results
- **MongoDB:** Agent states, round logs, community snapshots, memory logs
- **Celery + Redis:** Async simulation task queue

## Key Features

- **6-block structured prompting** — Identity → Behavioral → Moral framing → Social context → Memory → Action
- **Persuasion formula** — trust, argument quality, emotional resonance, social proof, repetition with hard stance caps
- **Community detection** — emergent group formation across simulation rounds
- **Memory compression** — agents summarize and retain relevant history
- **Hallucination checker** — three heuristics to flag low-quality LLM outputs
- **Counterfactual probing** — "what would have changed if X" analysis
- **Multi-provider LLM** — Anthropic (with prompt caching) or Ollama, swapped via `LLM_PROVIDER`

## Build Status

| Layer | Status |
|---|---|
| Phase 1 — Python CLI engine | ✅ |
| Phase 2A — FastAPI DB layer | ✅ |
| Phase 2B — Node/Express layer | ✅ |
| Phase 2C — Live integration smoke | ✅ |
| Phase 3 — Frontend wiring | ✅ |
| Phase 4 — Live sim, report, hallucination, memory, communities, edges | ✅ |

## Tech Stack

**Frontend:** React 18, TypeScript, Vite, Tailwind v4, Zustand, shadcn/ui, Framer Motion, Three.js, Recharts  
**Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 async, Alembic, Motor, Celery  
**Node:** Express, pg, ioredis, jsonwebtoken, ws  
**Infra:** PostgreSQL, MongoDB, Redis

## Setup

1. Copy `.env.example` → `.env` and fill in vars
2. Run migrations: `alembic upgrade head`
3. Start Redis, Postgres, MongoDB
4. Backend: `.venv\Scripts\activate && uvicorn backend.main:app --port 8000`
5. Node: `cd server && node index.js`
6. Frontend: `cd frontend && npm run dev`

## Testing

```bash
# Python
pytest tests/ -q

# Node
cd server && npm test

# Frontend
cd frontend && npx tsc --noEmit && npm test -- --run
Environment Variables
See .env.example for full list. Key vars: LLM_PROVIDER, ANTHROPIC_API_KEY, DATABASE_URL, MONGODB_URL, REDIS_URL, SECRET_KEY, FRONTEND_URL.
