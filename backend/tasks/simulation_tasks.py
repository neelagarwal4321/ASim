import asyncio
import logging
import os
import sys
import redis as sync_redis

_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import update
from tasks.celery_app import celery_app
from config import settings

logger = logging.getLogger(__name__)


def _get_redis():
    return sync_redis.from_url(settings.redis_url, decode_responses=True)


def _checkpoint_key(simulation_id: str) -> str:
    return f"sim:checkpoint:{simulation_id}"


def _active_key(user_id: str) -> str:
    return f"ratelimit:sim:active:{user_id}"


async def _persist_result(simulation_id: str, result: dict) -> None:
    from db.database import AsyncSessionLocal
    from db.models import SimulationResult as SimResultModel, SimulationConfig
    dist = result["distribution"]
    # Approximate avg_stance from bucketed distribution.
    # SimulationResult does not carry raw per-agent stance values at this stage;
    # use bucket midpoints as proxies (support≈0.8, undecided≈0.5, oppose≈0.2).
    # dist values are fractions (0–1) that sum to ~1.0, so the result is a
    # weighted average in [0.0, 1.0].
    avg_stance = (
        dist.get("support", 0) * 0.8
        + dist.get("undecided", 0) * 0.5
        + dist.get("oppose", 0) * 0.2
    )
    # Clamp to valid range
    avg_stance = max(0.0, min(1.0, round(avg_stance, 3)))
    async with AsyncSessionLocal() as session:
        session.add(SimResultModel(
            simulation_id=simulation_id,
            verdict=result["verdict"],
            confidence=result["confidence"],
            distribution=result["distribution"],
            avg_stance=avg_stance,
            narrative=result["narrative"],
            counterfactuals=result.get("counterfactuals", []),
            report=result.get("report", {}),
            hallucination_level=result.get("hallucination", {}).get("level", "green"),
        ))
        await session.execute(
            update(SimulationConfig)
            .where(SimulationConfig.id == simulation_id)
            .values(status="complete")
        )
        await session.commit()


async def _update_status(simulation_id: str, status: str) -> None:
    from db.database import AsyncSessionLocal
    from db.models import SimulationConfig
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
    user_id: str = "",
) -> dict:
    logger.info("run_full_simulation start: sim=%s agents=%d rounds=%d", simulation_id, agent_count, rounds)
    r = _get_redis()

    checkpoint = r.get(_checkpoint_key(simulation_id))
    start_round = int(checkpoint) if checkpoint else 0
    if start_round > 0:
        logger.info("Resuming sim=%s from round %d", simulation_id, start_round)

    try:
        from services.api_key_store import retrieve_api_key
        api_key = retrieve_api_key(simulation_id) if api_key_redis_key else None
    except Exception as exc:
        logger.warning("api_key_store unavailable: %s", exc)
        api_key = None

    async def _full_task() -> dict:
        from simulation.orchestrator import run_simulation
        sim_result = await run_simulation(
            scenario=scenario,
            agent_count=agent_count,
            rounds=rounds,
            seed=seed,
            api_key=api_key,
            simulation_id=simulation_id,
            start_round=start_round,
            checkpoint_fn=lambda rn: r.set(_checkpoint_key(simulation_id), rn, ex=7200),
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
            await _persist_result(simulation_id, result)
        except Exception as exc:
            logger.error("DB persist failed sim=%s: %s", simulation_id, exc)
            await _update_status(simulation_id, "failed")
        return result

    try:
        # checkpoint_fn writes sim:checkpoint:{id} = round_num after each round.
        # On task retry/restart, start_round resumes from the last completed round.
        result = asyncio.run(_full_task())

        r.delete(_checkpoint_key(simulation_id))
        if user_id:
            r.decr(_active_key(user_id))

        logger.info("run_full_simulation done: sim=%s verdict=%s", simulation_id, result["verdict"])
        return result

    except SoftTimeLimitExceeded:
        logger.warning("Soft time limit exceeded sim=%s", simulation_id)
        try:
            asyncio.run(_update_status(simulation_id, "failed"))
        except Exception:
            pass
        if user_id:
            r.decr(_active_key(user_id))
        r.delete(_checkpoint_key(simulation_id))
        raise

    except Exception as exc:
        logger.exception("run_full_simulation failed: sim=%s", simulation_id)
        try:
            asyncio.run(_update_status(simulation_id, "failed"))
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=5)
