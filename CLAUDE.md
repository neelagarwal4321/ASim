# CLAUDE.md — ASim

Multi-agent AI simulation engine. Hundreds of personality-distinct agents react to a scenario through emergent persuasion / trust / community formation. Output: verdict + narrative + counterfactual spectrum. Full design in `docs/ASim_Blueprint.docx` and `docs/ASim_Frontend.docx`.

## Architecture (hard boundary — never cross)

```
Frontend (React+TS+Vite, Tailwind v4, Zustand, Three.js)
   │ REST + WebSocket
   ▼
server/  Node + Express        ← user-facing only
   - JWT auth, OAuth (Google/GitHub), demo session
   - REST /api/v1/*, WebSocket /ws/simulate/:id (Redis fanout)
   - Postgres reads (pg), Redis pub/sub (ioredis)
   - X-API-Key extracted, forwarded in headers
   │ Internal HTTP localhost
   ▼
backend/  Python + FastAPI     ← simulation engine only
   - Agents, LLM via llm/executor.py, persuasion, output pipeline
   - SQLAlchemy 2.0 async + Alembic, Motor (Mongo), Celery, Redis publisher
```

**Node never:** simulation logic, LLM calls, agent code, Mongo.
**FastAPI never:** auth, sessions, frontend-facing routes, WebSocket endpoints.

## LLM Abstraction — Most Important Rule

Every LLM call goes through `backend/llm/executor.py`. No file outside `backend/llm/` imports `anthropic` or hits Ollama directly. `LLM_PROVIDER` env var picks provider. Anthropic provider must mark blocks 1-3 with `cache_control` (60-70% cost cut).

User API keys: come in `X-API-Key` header, forwarded per request, never stored, never logged.

## 6-Block Prompt — Order Is Load-Bearing

`backend/simulation/prompt_builder.py` builds every prompt in this exact order:

1. Identity (fixed)
2. Behavioral (fixed)
3. Moral framing (fixed)
4. Social context (dynamic)
5. Memory (dynamic)
6. Action + JSON spec (dynamic)

Identity must come before social context, otherwise agents conform to community instead of having personalities. Never reorder, merge, or skip. Block 6 always ends with the JSON block — parser depends on it; one retry on missing JSON, then skip agent for the round.

## Persuasion Formula — Strict

```
score = trust*0.30 + argument_quality*0.25 + emotional_resonance*0.20
      + social_proof*0.15 + min(0.30, repetition_bonus)*0.10

if score > target.susceptibility_threshold:
    delta = score * (1 - target.moral_rigidity) * 0.2 * direction
    delta = clamp(delta, -0.15, 0.15)            # hard cap
    if target.moral_rigidity >= 0.9:
        delta = clamp(delta, -0.02, 0.02)        # near-immovable
    target.stance = clamp(target.stance + delta, 0.0, 1.0)
```

Emotional resonance is 0 if appeal type doesn't match target emotion. `argument_quality` comes from the JSON block of each agent's response — not from confidence.

## Round Order (orchestrator)

scenario+events → independent prior → action select → 6-block prompt → parallel LLM → parse → persuasion → state → edges → community → memory compress → hallucination check → roundlog → ws emit. Do not reorder.

## Output Pipeline — Sequential Function Chain

`aggregator.compute_verdict()` → `narrative_synthesizer.generate()` → `counterfactual_prober.run_probes()` → `report_assembler.assemble()`. **Never** introduce LangChain or LangGraph.

## Databases

- **Postgres** (SQLAlchemy ORM only, Alembic migrations) — users, simulation_configs, agent_profiles, relationship_edges, simulation_results, injected_events. Node reads with `pg` + parameterized queries.
- **MongoDB** (Motor in Python only) — agent_states, round_logs, community_snapshots, agent_responses, memory_logs.

Never write raw SQL. Never insert untyped dicts into Mongo.

## Frontend Rules

TS only, no `.js` in `src/`. All API calls via `src/api/client.ts` (carries `Authorization` + `X-API-Key`). State in Zustand. shadcn/ui + Tailwind v4 + Recharts + Framer Motion + Three.js (only Landing hero + AgentGlobe). Aurora tokens in `styles/theme.css` — no hardcoded hex outside `AgentGlobe` archetype palette. WebSocket must connect with `?token=<jwt>` query param.

OAuth flow is server-side code-exchange: provider callback → backend stores short-lived `code` in Redis, redirects to `${FRONTEND_URL}/auth/callback?code=<code>` → frontend `OAuthCallback.tsx` POSTs `/auth/exchange` to receive tokens.

Routes are fixed in `src/App.tsx`. Do not invent new ones without spec update.

## Build State

| Layer | Status |
|---|---|
| Phase 1 — Python CLI engine | ✅ pytest green |
| Phase 2A — FastAPI DB layer | ✅ Pydantic+ORM+Mongo+Celery+Redis+API key store |
| Phase 2B — Node/Express layer | ✅ JWT/OAuth/WS/pubsub, 18 tests pass |
| Phase 2C — Live integration smoke | ✅ verified end-to-end (Node → FastAPI → Celery → Ollama → Redis pubsub → Postgres) |
| Phase 3 — Frontend wiring | ✅ 17 tests pass, tsc clean |
| Phase 4 — Live sim, report, hallucination, memory, communities, edges | ✅ 126 Python tests pass |

## Workflow

- Activate venv first: `.venv\Scripts\activate`. Python tests: `pytest tests/ -q`.
- Node: `cd server && npm test`. Boot: `node -e "require('./index')"`.
- Frontend: `cd frontend && npx tsc --noEmit && npm test -- --run`.
- Run that layer's tests after every change. Don't claim done without green.
- Subagents for multi-file work; Haiku mechanical, Sonnet orchestration; Opus only when requested.
- Plan before code on 3+ step or architectural tasks.

## Environment

All config in `.env` (see `.env.example`). Key vars: `LLM_PROVIDER`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL=claude-sonnet-4-6`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `DATABASE_URL` (asyncpg), `DATABASE_URL_NODE` (pg), `MONGODB_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `SECRET_KEY`, `JWT_EXPIRY`, `NODE_PORT=3000`, `FASTAPI_PORT=8000`, `FASTAPI_INTERNAL_URL`, OAuth IDs/secrets, `OAUTH_CALLBACK_BASE`, `FRONTEND_URL`, optional `VITE_API_BASE_URL`, `VITE_WS_BASE_URL`. `NODE_ENV` controls server CORS + log level (no `APP_ENV`).

## Hard Don'ts

- No LLM call outside `backend/llm/`.
- No raw SQL; no Mongo from Node.
- No reorder/merge/skip of the 6 prompt blocks; no omission of the JSON block.
- No stance delta > 0.15 per round; no LangChain/LangGraph anywhere.
- No `print()` in backend — use `logging`.
- No commit of `.env`.
- No new frontend pages/routes outside `docs/ASim_Frontend.docx` without explicit instruction.
- No agent-orchestration framework around the output pipeline.
- No storing or logging of user API keys.

## Reference

| Need | Source |
|---|---|
| Agent design (traits, archetypes) | Blueprint §02 |
| Round + persuasion | Blueprint §03 |
| Graph + community | Blueprint §04 |
| Prompt + memory | Blueprint §05 |
| Modes + config | Blueprint §06 |
| Output pipeline | Blueprint §07 |
| Data entities | Blueprint §08 |
| Components | Blueprint §09 |
| Phase plan | Blueprint §11 |
| Frontend pages, design tokens | `docs/ASim_Frontend.docx` |
