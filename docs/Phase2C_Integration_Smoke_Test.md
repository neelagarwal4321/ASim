# Phase 2C Integration Smoke Test

**Status:** Pending. Requires live Postgres + Redis. This document describes the exact steps to verify Phase 2C.

---

## Prerequisites

Before running smoke test, verify:

1. **Postgres running**
   - Supabase project created and connection string in `.env` as `DATABASE_URL`
   - OR local Postgres on port 5432 with `asim` database

2. **Redis running**
   - Upstash Redis created and URL in `.env` as `REDIS_URL`
   - OR local Redis on port 6379

3. **Ollama running**
   - `ollama pull llama3.1:8b` completed
   - `ollama serve` running on localhost:11434

4. **Environment**
   ```bash
   # Activate venv
   .venv\Scripts\activate
   
   # Verify .env has all required vars
   cat .env | grep -E "DATABASE_URL|REDIS_URL|OLLAMA|LLM_PROVIDER"
   
   # Verify LLM_PROVIDER=ollama (not anthropic)
   ```

---

## Test Sequence

### 1. Apply all database migrations

```bash
cd backend
alembic upgrade head
```

Expected: All migrations applied without error. Schema includes:
- `users` table
- `simulation_configs` table
- `agent_profiles` table
- `relationship_edges` table
- `simulation_results` table
- `injected_events` table

### 2. Start FastAPI backend

```bash
cd backend
python main.py
```

Expected: Server starts on port 8000, logs "Uvicorn running on http://127.0.0.1:8000"

### 3. Start Node server (separate terminal)

```bash
cd server
npm install
node index.js
```

Expected: Server starts on port 3000, logs "Server listening on port 3000"

### 4. Run Node integration tests

```bash
cd server
npm test -- --testTimeout=30000
```

Expected: All 18 tests pass:
- auth.test.js: 6 tests (signup/login validation, database unavailable, demo auth, token rotation)
- simulation.test.js: 12 tests (CRUD, pause/resume, agent management, WebSocket)

### 5. Run Python integration tests

```bash
cd backend
pytest tests/ -v
```

Expected: All 46 tests pass across:
- llm/ (executor, response parser, Ollama provider)
- agents/ (generation, archetypes, voice styles)
- simulation/ (orchestrator, prompt builder, persuasion engine, action selector, state manager)
- api/ (health check, internal simulation endpoints)

### 6. Quick manual test: CLI simulation

```bash
cd backend
python cli.py --scenario "Universal Basic Income" --agents 5 --rounds 2
```

Expected: Completes in <30s for 5 agents × 2 rounds. Output shows:
- Dominant outcome with % confidence
- Top 3 influential agents by persuasion impact
- 3-5 sentence narrative arc

### 7. WebSocket streaming test (optional, requires frontend)

Start frontend:
```bash
cd frontend
npm install
npm run dev
```

Then in browser:
1. Navigate to http://localhost:5173/app/dashboard
2. Click "New Simulation"
3. Submit scenario with 10 agents, 3 rounds
4. Should redirect to live simulation page
5. Watch agent messages stream in real-time

Expected: Messages arrive every few seconds as rounds complete.

---

## Success Criteria

✅ All migrations apply cleanly  
✅ FastAPI boots and serves /health  
✅ Node boots and serves auth routes  
✅ All Node tests pass (18/18)  
✅ All Python tests pass (46/46)  
✅ CLI simulation produces a verdict + narrative  
✅ WebSocket streaming works (optional)  

---

## Debugging

| Issue | Fix |
|-------|-----|
| `psycopg2.OperationalError: could not translate host name "host"` | DATABASE_URL malformed. Check Supabase credentials. |
| `ConnectionRefusedError: Cannot connect to localhost:6379` | Redis not running. Start with `redis-cli ping` or verify REDIS_URL. |
| `No module named 'backend.config'` | Venv not activated. Run `.venv\Scripts\activate`. |
| `OLLAMA_BASE_URL connection refused` | Ollama not running. Start with `ollama serve`. |
| Tests timeout | Increase `--testTimeout` flag. Network latency or slow LLM. |

---

## Notes

- Phase 2C includes: Postgres ORM (SQLAlchemy), MongoDB Motor client, Alembic migrations, async FastAPI, Node REST routes, WebSocket server, Redis pub/sub.
- Phase 2B was auth (JWT, OAuth). Phase 2C adds the database layer and integration.
- Phase 3 will wire frontend to real API (replacing mock data).
- Once Phase 2C passes, mark "Backend Phase 2C — Integration verified" as ✅ Complete in CLAUDE.md.

