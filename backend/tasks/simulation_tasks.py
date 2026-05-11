import asyncio
import logging
from sqlalchemy import update
from tasks.celery_app import celery_app
from db.database import AsyncSessionLocal
from db.models import SimulationResult as SimResultModel, SimulationConfig

logger = logging.getLogger(__name__)


async def _persist_result(simulation_id: str, result: dict) -> None:
    """Write verdict/narrative to simulation_results; flip simulation to complete."""
    dist = result["distribution"]
    avg_stance = (
        dist.get("support", 0) * 0.8
        + dist.get("undecided", 0) * 0.5
        + dist.get("oppose", 0) * 0.2
    )
    async with AsyncSessionLocal() as session:
        hallucination_level = result.get("hallucination", {}).get("level", "green")
        session.add(SimResultModel(
            simulation_id=simulation_id,
            verdict=result["verdict"],
            confidence=result["confidence"],
            distribution=result["distribution"],
            avg_stance=round(avg_stance, 3),
            narrative=result["narrative"],
            counterfactuals=result.get("counterfactuals", []),
            report=result.get("report", {}),
            hallucination_level=hallucination_level,
        ))
        await session.execute(
            update(SimulationConfig)
            .where(SimulationConfig.id == simulation_id)
            .values(status="complete")
        )
        await session.commit()


async def _update_status(simulation_id: str, status: str) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(SimulationConfig)
            .where(SimulationConfig.id == simulation_id)
            .values(status=status)
        )
        await session.commit()


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
    logger.info("run_full_simulation start: sim=%s scenario=%.50s agents=%d rounds=%d",
                simulation_id, scenario, agent_count, rounds)
    try:
        from services.api_key_store import retrieve_api_key
        api_key = retrieve_api_key(simulation_id) if api_key_redis_key else None
    except Exception as exc:
        logger.warning("api_key_store unavailable: %s — running without key", exc)
        api_key = None

    from simulation.orchestrator import run_simulation
    loop = asyncio.new_event_loop()
    try:
        sim_result = loop.run_until_complete(
            run_simulation(
                scenario=scenario,
                agent_count=agent_count,
                rounds=rounds,
                seed=seed,
                api_key=api_key,
                simulation_id=simulation_id,
            )
        )
        result = {
            "simulation_id": simulation_id,
            "verdict": sim_result.verdict,
            "confidence": sim_result.confidence,
            "distribution": sim_result.distribution,
            "narrative": sim_result.narrative,
            "counterfactuals": sim_result.counterfactuals,
            "hallucination": sim_result.hallucination,
            "report": sim_result.report,
            "status": "complete",
        }
        try:
            loop.run_until_complete(_persist_result(simulation_id, result))
        except Exception as exc:
            logger.error("DB persist failed sim=%s: %s", simulation_id, exc)
            loop.run_until_complete(_update_status(simulation_id, "failed"))
        logger.info("run_full_simulation done: sim=%s verdict=%s", simulation_id, sim_result.verdict)
        return result
    except Exception as exc:
        logger.exception("run_full_simulation failed: sim=%s", simulation_id)
        try:
            loop.run_until_complete(_update_status(simulation_id, "failed"))
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=5)
    finally:
        loop.close()
