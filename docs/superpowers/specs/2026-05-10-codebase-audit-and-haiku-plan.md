# ASim Codebase Audit + Haiku Execution Plan — 2026-05-10

## 1. What ASim Is (recap)

Multi-agent AI simulation engine. Hundreds of personality-distinct agents respond to a scenario through emergent social behavior (persuasion, trust graph, communities). Outputs: dominant verdict + narrative arc + counterfactual spectrum. Dual-backend: Node/Express handles user-facing layer (auth, REST, WebSocket fan-out, Postgres reads, Redis pub/sub); Python FastAPI handles simulation engine (agents, LLM via `llm/executor.py`, persuasion math, output pipeline, Redis publish). Frontend React+TS+Vite+Tailwind v4+Zustand+Three.js.

## 2. Tech Stack Inventory (verified)

| Layer | Stack | Status |
|-------|-------|--------|
| Python backend | FastAPI, SQLAlchemy 2.0 async, Alembic, Motor (Mongo), Celery, Redis, NetworkX, Pydantic | Phase 1+2A complete; tests **88/88 pass** |
| Node server | Express, ws, pg, ioredis, JWT, bcrypt, passport (Google+GitHub), express-validator, helmet, cors, morgan, winston | Phase 2B complete; tests **18/18 pass**; boot OK |
| Frontend | React 19, Vite, TS strict, Tailwind v4 (@tailwindcss/vite), Zustand, axios, react-router-dom, Three.js, Framer Motion, Recharts, shadcn/ui | Phase 3 mostly wired; **16/16 tests pass**; tsc clean |
| Infra | Postgres (Supabase), Redis (Upstash), MongoDB Atlas, Ollama for dev / Anthropic for prod | Phase 2C **integration smoke test pending** |

Architecture rules from CLAUDE.md verified intact: 6-block prompt order correct, persuasion weights correct (0.30/0.25/0.20/0.15/0.10), stance clamps correct, no LangChain anywhere, no LLM calls outside `backend/llm/`, no auth in FastAPI.

## 3. Verified Issue List

Findings cross-checked against source. Subagent-reported issues that proved false on inspection have been excluded.

### BLOCKERS (break user-facing flows)

| ID | File:Line | Problem | Fix Direction |
|----|-----------|---------|---------------|
| **B1** | `server/routes/auth.js:36-43,135-153` ↔ `frontend/src/pages/auth/OAuthCallback.tsx:10-24` | OAuth flow mismatch. Backend redirects to `/auth/callback?code=<code>` (server-side code exchange). Frontend reads `accessToken`/`refreshToken` directly from URL. **OAuth login completely broken.** | Update frontend `OAuthCallback.tsx` to POST `/auth/exchange` with `code` and store returned tokens. Handoff doc was outdated. |
| **B2** | `frontend/src/api/websocket.ts:28` ↔ `server/websocket/server.js:16-17` | Frontend WS connect omits `?token=`; server requires token query-param and 401s without it. **Live simulation never connects.** | Inject `accessToken` from `authStore` as `?token=` query string in `connect()`. |
| **B3** | `frontend/src/pages/app/Dashboard.tsx:116` | `const HAS_SIMULATIONS = true` hardcoded; gates UI sections regardless of real data. | Replace with `recentSims.length > 0`. |
| **B4** | `server/routes/auth.js:125-131` and `server/routes/users.js:9-18` | Two `GET /me` routes mounted under `/api/v1/auth/me` AND `/api/v1/users/me`. Both query DB. Two sources of truth. | Remove from `auth.js`, keep `users.js`. |

### CORRECTNESS (subtle bugs / spec violations)

| ID | File:Line | Problem | Fix |
|----|-----------|---------|-----|
| **C1** | `server/index.js:25` | CORS dev branch keys on `APP_ENV` but everything else (`logger.js`, tests) uses `NODE_ENV`. CORS may permit/deny incorrectly across deploys. | Switch to `process.env.NODE_ENV !== 'production'`. |
| **C2** | `backend/simulation/persuasion_engine.py:27` | Uses `actor_action.confidence` for the 0.25 weight slot. Blueprint specifies `argument_quality(A)`. Agent JSON output already reports `argument_quality`. | Plumb `argument_quality` from parsed action through orchestrator into `resolve_persuasion(...)`. Confidence ≠ argument quality. |
| **C3** | `server/services/simulationService.js` (`controlSimulation`) | Does not forward `X-API-Key` header to FastAPI. Pause/resume/cancel calls drop user key. | Accept `apiKey` param; conditionally set header (mirror `startSimulation`). |
| **C4** | `server/websocket/server.js:49-63` | `sub.on('message', …)` is attached on **every** new simulation subscription; only `sub.subscribe()` is gated by the `subscribedSims` Set. Listeners accumulate; over time message-fanout cost grows linearly with all sims ever subscribed in this process. | Move single global `sub.on('message', …)` to outside `subscribeIfNeeded`; keep only `subscribe()` per-sim. |
| **C5** | `server/websocket/server.js:54` | `logger.error('Redis subscribe error: %s', err.message)` — winston `printf` setup does not interpret `%s`. Logs print literal `%s`. | Template literal: `` `Redis subscribe error: ${err.message}` ``. |
| **C6** | `frontend/src/api/client.ts:40` ↔ `server/routes/auth.js:92` | Refresh body uses `{ refreshToken }` (camelCase). Server reads `req.body.refreshToken` — **matches**. (Subagent claim of mismatch was incorrect; flagging as VERIFIED OK so haiku doesn't "fix" it.) | NO-OP. Documented to prevent regressions. |

### DRIFT (cleanup, no runtime impact)

| ID | File | Problem | Fix |
|----|------|---------|-----|
| **D1** | `server/db/mongo.js`, `server/package.json` (`mongoose`) | Node imports mongoose & defines `connectMongo` but never calls it. Architecture forbids Mongo from Node side. | Delete `server/db/mongo.js`; remove `mongoose` from `server/package.json`; run `npm prune`. |
| **D2** | `AGENTS.md` (root) | Codex-generated duplicate of `CLAUDE.md` with name-substitutions; contains typo `ANTHROPIC_MODEL=Codex-sonnet-4-6` (line 321). | Replace `AGENTS.md` with a one-line pointer: "See `CLAUDE.md`. Treat it as the source of truth for any agent in this repo." |
| **D3** | `backend/graph/__init__.py`, `backend/memory/__init__.py` | Empty stubs. No modules. Phase 2 deliverables (community detection, memory compression, hallucination checker) not implemented. Documented as Phase 2 in `CLAUDE.md` build state. | Add comment in each `__init__.py`: `# Phase 2 — not yet implemented. See CLAUDE.md build state.` Do not auto-import; nothing depends on them yet. |
| **D4** | `frontend/src/pages/app/Dashboard.tsx` (mock data block lines 60-107) | Mock metric/series data still present. Used only when `HAS_SIMULATIONS=false` (or after B3 fix, when real list empty). Acceptable for empty-state demo. | Keep, but mark with a clear comment block: `// EMPTY-STATE PLACEHOLDER — replaced when sims load`. |
| **D5** | `.env.example` | (verify whether `ANTHROPIC_MODEL` is correct value) | Confirm `ANTHROPIC_MODEL=claude-sonnet-4-6` (not `Codex-…`). |
| **D6** | Phase 2C integration | Not run since real Postgres/Redis are not available locally. CLAUDE.md flags this. | Document the manual smoke-test steps in `docs/phase2c_smoke_test.md`. Not haiku-executable until infra available. |

## 4. Split: Opus Fixes Now vs. Haiku Executes

**Opus this session (architectural / multi-file judgment calls):**

- **B1** OAuth callback rewrite — touches frontend route, calls new endpoint, error handling.
- **B2** WS auth — touches both stores and connect lifecycle.
- **B4** duplicate `/me` removal — must decide canonical, ensure callers untouched.
- **C1** env-var rename — security-adjacent, must verify no test breaks.
- **C2** persuasion `argument_quality` plumbing — touches orchestrator + persuasion_engine + tests.
- **C4** WS subscriber listener move — risk of breaking fanout.
- **D2** AGENTS.md replacement — single decision file.

**Haiku tasks (mechanical, single-file, exact spec):**

- **B3** Dashboard `HAS_SIMULATIONS` flag → derived expression.
- **C3** `controlSimulation` apiKey forward.
- **C5** WS log template-literal.
- **D1** delete `server/db/mongo.js` + remove mongoose dep.
- **D3** stub `__init__.py` comments.
- **D4** Dashboard mock-data comment.
- **D5** `.env.example` model-name verify/fix.
- **D6** write `docs/phase2c_smoke_test.md`.

## 5. Haiku Execution Plan

Each task below is **single-file, ≤30 lines changed, with exact before/after**. Haiku must:

1. Activate venv if Python: `.venv\Scripts\activate`.
2. Read the file FIRST with the Read tool.
3. Make the edit with Edit tool exactly as specified.
4. Run the verification command. Paste tail of output.
5. Only proceed to next task if verification passes.

### TASK H1 — Dashboard empty-state flag

**File:** `frontend/src/pages/app/Dashboard.tsx`
**Find context:** locate the section where `recentSims` state is read (search for `recentSims`).
**Change line 116:**
```diff
-// Set to false to see the empty state
-const HAS_SIMULATIONS = true
+// Replaced when sims load — empty state shown when zero results.
```
Then, inside the component, replace every `HAS_SIMULATIONS` reference with `recentSims.length > 0`.
**Verify:** `cd frontend; npx tsc --noEmit`. Must pass with zero errors.

### TASK H2 — Forward apiKey on control endpoint

**File:** `server/services/simulationService.js`
**Find function:** `controlSimulation(simulationId, action, apiKey)` — current signature does NOT accept apiKey.
**Change:**
```diff
-async function controlSimulation(simulationId, action) {
-  return axios.post(`${BASE}/internal/simulate/${simulationId}/control`, { action });
+async function controlSimulation(simulationId, action, apiKey) {
+  const headers = apiKey ? { 'X-API-Key': apiKey } : {};
+  return axios.post(`${BASE}/internal/simulate/${simulationId}/control`, { action }, { headers });
 }
```
Then in `server/routes/simulation.js` line 102, pass `req.apiKey`:
```diff
-      await controlSimulation(req.params.id, req.body.action);
+      await controlSimulation(req.params.id, req.body.action, req.apiKey);
```
And add `extractApiKey` middleware to that route at line 97.
**Verify:** `cd server; npm test`. Must show 18 passing (or more, no regressions).

### TASK H3 — WS log format fix

**File:** `server/websocket/server.js`
**Change line 54:**
```diff
-    if (err) logger.error('Redis subscribe error: %s', err.message);
+    if (err) logger.error(`Redis subscribe error: ${err.message}`);
```
**Verify:** `cd server; node -e "require('./index')"` — must exit 0 with no output.

### TASK H4 — Delete unused mongo bindings

**Files:**
- Delete `server/db/mongo.js` entirely.
- Edit `server/package.json` — remove the `"mongoose": "..."` line from `dependencies`.
- Run `cd server; rm -rf node_modules; npm install` (or `npm prune`).
**Verify:** `cd server; node -e "require('./index')"` and `npm test`. Boot succeeds, all tests pass.

### TASK H5 — Phase 2 stub markers

**Files:** `backend/graph/__init__.py`, `backend/memory/__init__.py`
**Replace contents (each file):**
```python
# Phase 2 — community detection / memory compression / hallucination checker.
# Not yet implemented. See CLAUDE.md "Current Build State" table.
```
**Verify:** `.venv\Scripts\python.exe -m pytest tests/ -q --tb=line`. Must remain 88 passing.

### TASK H6 — Dashboard mock data label

**File:** `frontend/src/pages/app/Dashboard.tsx`
**Above the mock data block (around line 60), insert:**
```ts
// ── EMPTY-STATE PLACEHOLDER ─────────────────────────────────────────────
// Used when the user has no simulations yet; replaced once recentSims loads.
```
**Verify:** `cd frontend; npx tsc --noEmit`. Pass.

### TASK H7 — Verify `.env.example` model name

**File:** `.env.example`
**Search line containing `ANTHROPIC_MODEL=`. Required value:** `ANTHROPIC_MODEL=claude-sonnet-4-6`. If it shows `Codex-sonnet-4-6` or anything else, fix it.
**Verify:** grep returns exactly one line equal to the required value.

### TASK H8 — Phase 2C smoke test doc

**Create file:** `docs/phase2c_smoke_test.md` with body (verbatim):
```markdown
# Phase 2C — Integration Smoke Test (manual)

Prereqs: real Postgres (Supabase URL in `.env`), real Redis (Upstash URL), Ollama running.

1. `.venv\Scripts\activate`
2. `alembic -c backend/db/migrations/alembic.ini upgrade head`
3. `python -m uvicorn backend.main:app --port 8000 --reload`
4. Separate shell: `cd server; npm start`
5. Separate shell: `cd frontend; npm run dev`
6. POST to `http://localhost:3000/api/v1/auth/demo` → demo tokens.
7. POST to `http://localhost:3000/api/v1/simulate` with `{ "scenario": "test", "agentCount": 5, "rounds": 1 }` plus `Authorization: Bearer <demo-access>`.
8. Open ws connection: `ws://localhost:3000/ws/simulate/<id>?token=<demo-access>`.
9. Verify a `round_log` message arrives within ~30s.

Pass: round_log received, no exceptions in either backend log.
Fail: capture log lines and the failing step.
```

## 6. Verification Gates (run after each phase)

- After Opus fixes: `npm test` (server) + `npm test` (frontend) + `pytest tests/` + `npx tsc --noEmit`.
- After every haiku task: the task's listed Verify command. **Do not advance on red.**
- Before merge: full suite green + boot tests green.

## 7. Out-of-Scope (explicitly not addressed)

- Three.js geometry leak in `AgentGlobe` grid lines — reported by frontend audit; existing `AgentGlobe` cleanup at lines 364-393 already disposes most resources. Marginal leak, defer.
- Counterfactual prober + report assembler implementation — Phase 4.
- Memory compression + hallucination checker — Phase 4.
- Phase 4 frontend pages (LiveSimulation full wiring beyond WS auth fix; Report final wiring; History/Settings full features).
- Real Phase 2C run (needs live Postgres + Redis).

## 8. Risks for Haiku

- Haiku tends to drift on multi-file edits; tasks above are **single-file by design**. H2 is the only multi-file task and is small.
- Haiku may "improve" code beyond instructions; scripted Edit calls with exact diffs reduce that risk.
- Haiku must run verify commands EVERY time. Without that, silent breakage.
- Haiku must NOT touch any architectural rules (LLM abstraction, 6-block order, persuasion formula weights, dual-backend boundary).

---

End of spec.
