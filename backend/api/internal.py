from fastapi import APIRouter

router = APIRouter(prefix="/internal")


@router.post("/simulate/start")
async def start_simulation(body: dict) -> dict:
    # Phase 2: call orchestrator as Celery task
    return {"ok": False, "message": "Not implemented in Phase 1 — use CLI"}
