import asyncio
import datetime
import logging
import uuid

import redis as sync_redis
from celery import shared_task

from config import settings

logger = logging.getLogger(__name__)


def _get_redis():
    return sync_redis.from_url(settings.redis_url, decode_responses=True)


def _extract_sim_ids_from_api_keys(keys: list[str]) -> list[str]:
    return [k.replace('apikey:', '') for k in keys if k.startswith('apikey:')]


def _is_stale(updated_at: datetime.datetime, max_duration_seconds: int) -> bool:
    age = (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - updated_at).total_seconds()
    return age > max_duration_seconds


@shared_task(name="tasks.cleanup_expired_api_keys")
def cleanup_expired_api_keys():
    """Delete apikey: Redis keys for simulations that are complete/failed/cancelled."""
    r = _get_redis()
    keys = list(r.scan_iter('apikey:*'))
    if not keys:
        return {"deleted": 0}

    sim_ids = _extract_sim_ids_from_api_keys(keys)

    async def _fetch_statuses():
        from db.database import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT id, status FROM simulation_configs WHERE id = ANY(:ids)"),
                {"ids": sim_ids}
            )
            return {row[0]: row[1] for row in result.fetchall()}

    statuses = asyncio.run(_fetch_statuses())
    terminal = {'complete', 'failed', 'cancelled'}
    deleted = 0
    for sim_id in sim_ids:
        if statuses.get(sim_id) in terminal:
            r.delete(f"apikey:{sim_id}")
            deleted += 1

    logger.info("cleanup_expired_api_keys: deleted %d orphaned keys", deleted)
    return {"deleted": deleted}


@shared_task(name="tasks.archive_old_simulations")
def archive_old_simulations():
    """Move round_logs older than 90 days to round_logs_archive MongoDB collection."""
    from motor.motor_asyncio import AsyncIOMotorClient

    async def _archive():
        client = AsyncIOMotorClient(settings.mongodb_url)
        db = client[settings.mongodb_db]
        cutoff = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=90)

        cursor = db.round_logs.find({"created_at": {"$lt": cutoff}}, batch_size=100)
        moved = 0
        async for doc in cursor:
            await db.round_logs_archive.insert_one(doc)
            await db.round_logs.delete_one({"_id": doc["_id"]})
            moved += 1
        client.close()
        return moved

    moved = asyncio.run(_archive())
    logger.info("archive_old_simulations: moved %d documents to round_logs_archive", moved)
    return {"archived": moved}


@shared_task(name="tasks.retry_failed_simulations")
def retry_failed_simulations():
    """Re-enqueue simulations that failed with retry_count < 3."""
    async def _fetch_retryable():
        from db.database import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("""
                SELECT id, user_id, scenario, agent_count, rounds, seed
                FROM simulation_configs
                WHERE status = 'failed'
                  AND retry_count < 3
                  AND updated_at < NOW() - INTERVAL '5 minutes'
                  AND deleted_at IS NULL
                LIMIT 10
            """))
            return result.fetchall()

    async def _increment_retry(sim_id: str):
        from db.database import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("UPDATE simulation_configs SET retry_count = retry_count + 1, status = 'pending' WHERE id = :id"),
                {"id": sim_id}
            )
            await session.commit()

    rows = asyncio.run(_fetch_retryable())
    if not rows:
        return {"requeued": 0}

    from tasks.simulation_tasks import run_full_simulation
    requeued = 0
    for row in rows:
        sim_id, user_id, scenario, agent_count, rounds, seed = row
        asyncio.run(_increment_retry(sim_id))
        run_full_simulation.apply_async(
            args=[sim_id, scenario, agent_count, rounds, seed, '', user_id],
            queue='default'
        )
        requeued += 1
        logger.info("retry_failed_simulations: requeued sim=%s", sim_id)

    return {"requeued": requeued}


@shared_task(name="tasks.rollup_daily_metrics")
def rollup_daily_metrics():
    """Aggregate yesterday's simulation stats into metrics_rollup table."""
    async def _rollup():
        from db.database import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            yesterday = (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=1)).date()
            result = await session.execute(text("""
                SELECT COUNT(*) as total, AVG(rounds) as avg_rounds
                FROM simulation_configs
                WHERE DATE(created_at) = :date AND deleted_at IS NULL
            """), {"date": yesterday})
            row = result.fetchone()
            total = row[0] or 0
            avg_rounds = float(row[1]) if row[1] else None

            await session.execute(text("""
                INSERT INTO metrics_rollup(id, date, total_sims, avg_rounds)
                VALUES(:id, :date, :total, :avg_rounds)
                ON CONFLICT (date) DO UPDATE
                SET total_sims = :total, avg_rounds = :avg_rounds
            """), {"id": str(uuid.uuid4()), "date": yesterday, "total": total, "avg_rounds": avg_rounds})
            await session.commit()
        return {"date": str(yesterday), "total": total}

    result = asyncio.run(_rollup())
    logger.info("rollup_daily_metrics: %s", result)
    return result


@shared_task(name="tasks.postgres_vacuum_analyze")
def postgres_vacuum_analyze():
    """Run VACUUM ANALYZE on high-write tables."""
    import asyncpg

    async def _vacuum():
        conn = await asyncpg.connect(settings.database_url.replace('+asyncpg', ''))
        tables = ['simulation_configs', 'agent_profiles', 'relationship_edges', 'refresh_tokens']
        for table in tables:
            await conn.execute(f'VACUUM ANALYZE {table}')
            logger.info("VACUUM ANALYZE completed: %s", table)
        await conn.close()

    asyncio.run(_vacuum())
    return {"ok": True}


@shared_task(name="tasks.watchdog_stale_sims")
def watchdog_stale_sims():
    """Find simulations stuck in 'running' beyond max_duration and force-fail them."""
    async def _fix_stale():
        from db.database import AsyncSessionLocal
        from sqlalchemy import text
        r = _get_redis()
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("""
                SELECT sc.id, sc.user_id, sc.updated_at, tc.max_duration_seconds
                FROM simulation_configs sc
                JOIN users u ON u.id = sc.user_id
                JOIN tier_config tc ON tc.role = u.role
                WHERE sc.status = 'running'
                  AND sc.deleted_at IS NULL
            """))
            rows = result.fetchall()
            fixed = 0
            for sim_id, user_id, updated_at, max_dur in rows:
                if _is_stale(updated_at, max_dur):
                    await session.execute(
                        text("UPDATE simulation_configs SET status='failed' WHERE id=:id"),
                        {"id": sim_id}
                    )
                    key = f"ratelimit:sim:active:{user_id}"
                    val = r.decr(key)
                    if val < 0:
                        r.set(key, 0)
                    fixed += 1
                    logger.warning("watchdog: force-failed stale sim=%s user=%s", sim_id, user_id)
            await session.commit()
            return fixed

    fixed = asyncio.run(_fix_stale())
    return {"fixed": fixed}
