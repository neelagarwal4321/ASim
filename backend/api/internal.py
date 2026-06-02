import logging
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal")


def _check_internal(x_internal_secret: str = Header(default="")):
    # Use INTERNAL_API_SECRET if set, otherwise fall back to SECRET_KEY.
    # Always enforce — never allow through when expected secret is empty.
    expected = settings.internal_api_secret or settings.secret_key
    if not expected or x_internal_secret != expected:
        raise HTTPException(status_code=403, detail="Forbidden")


class SimulationStartRequest(BaseModel):
    simulation_id: str
    scenario: str
    agent_count: int = 50
    rounds: int = 5
    seed: int | None = None
    api_key_redis_key: str | None = None


class SimulationStartResponse(BaseModel):
    ok: bool
    simulation_id: str
    message: str


class SimulationStatusResponse(BaseModel):
    simulation_id: str
    status: str


class InjectEventRequest(BaseModel):
    simulation_id: str
    round_num: int
    event_text: str


class ControlRequest(BaseModel):
    action: str  # "pause" | "resume" | "cancel"


@router.post("/simulate/start", response_model=SimulationStartResponse, dependencies=[Depends(_check_internal)])
async def start_simulation(body: SimulationStartRequest) -> SimulationStartResponse:
    """Kick off a simulation via Celery task."""
    logger.info("start_simulation: id=%s scenario=%.50s", body.simulation_id, body.scenario)
    from tasks.simulation_tasks import run_full_simulation  # noqa: PLC0415
    run_full_simulation.delay(
        body.simulation_id,
        body.scenario,
        body.agent_count,
        body.rounds,
        body.seed,
        body.api_key_redis_key or "",
    )
    return SimulationStartResponse(
        ok=True,
        simulation_id=body.simulation_id,
        message="Simulation queued",
    )


@router.get("/simulate/{simulation_id}/status", response_model=SimulationStatusResponse, dependencies=[Depends(_check_internal)])
async def get_simulation_status(simulation_id: str) -> SimulationStatusResponse:
    return SimulationStatusResponse(simulation_id=simulation_id, status="unknown")


@router.post("/simulate/{simulation_id}/inject-event", dependencies=[Depends(_check_internal)])
async def inject_event(simulation_id: str, body: InjectEventRequest) -> dict:
    logger.info("inject_event: sim=%s round=%d", simulation_id, body.round_num)
    return {"ok": True, "simulation_id": simulation_id}


@router.post("/simulate/{simulation_id}/control", dependencies=[Depends(_check_internal)])
async def control_simulation(simulation_id: str, body: ControlRequest) -> dict:
    logger.info("control: sim=%s action=%s", simulation_id, body.action)
    return {"ok": True, "simulation_id": simulation_id, "action": body.action}


@router.get("/agents/{agent_id}", dependencies=[Depends(_check_internal)])
async def get_agent(agent_id: str) -> dict:
    return {"agent_id": agent_id, "status": "stub"}
