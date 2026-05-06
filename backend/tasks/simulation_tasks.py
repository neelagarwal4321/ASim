import asyncio
import logging
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.run_full_simulation", bind=True, max_retries=3)
def run_full_simulation(
    self,
    simulation_id: str,
    scenario: str,
    agent_count: int,
    rounds: int,
    seed: int | None,
    api_key_redis_key: str,
) -> dict:
    """Run a full simulation synchronously inside a Celery worker."""
    logger.info("run_full_simulation start: sim=%s scenario=%.50s agents=%d rounds=%d",
                simulation_id, scenario, agent_count, rounds)
    try:
        from services.api_key_store import retrieve_api_key
        api_key = retrieve_api_key(simulation_id) if api_key_redis_key else None
    except Exception as exc:
        logger.warning("api_key_store unavailable: %s — running without key", exc)
        api_key = None

    try:
        from simulation.orchestrator import run_simulation
        result = asyncio.run(
            run_simulation(
                scenario=scenario,
                agent_count=agent_count,
                rounds=rounds,
                seed=seed,
                api_key=api_key,
            )
        )
        logger.info("run_full_simulation done: sim=%s verdict=%s", simulation_id, result.verdict)
        return {
            "simulation_id": simulation_id,
            "verdict": result.verdict,
            "confidence": result.confidence,
            "distribution": result.distribution,
            "narrative": result.narrative,
            "status": "complete",
        }
    except Exception as exc:
        logger.exception("run_full_simulation failed: sim=%s", simulation_id)
        raise self.retry(exc=exc, countdown=5)
