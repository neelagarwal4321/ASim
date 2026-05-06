import asyncio
import logging
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.run_agent_round", bind=True, max_retries=2)
def run_agent_round(self, simulation_id: str, agent_id: str, round_num: int) -> dict:
    """Phase 2 stub — Phase 1 uses sequential loop in orchestrator."""
    logger.info("run_agent_round: sim=%s agent=%s round=%d", simulation_id, agent_id, round_num)
    return {"simulation_id": simulation_id, "agent_id": agent_id, "round_num": round_num, "status": "stub"}
