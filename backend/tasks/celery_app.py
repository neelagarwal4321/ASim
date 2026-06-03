import logging
import os
import sys

# Ensure backend/ is on sys.path so all backend modules resolve correctly
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from celery import Celery
from celery.signals import worker_init
from config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "asim",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["tasks.simulation_tasks", "tasks.cron_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_soft_time_limit=7200,
    task_time_limit=7500,
    beat_scheduler="redbeat.RedBeatScheduler",
    redbeat_redis_url=settings.redis_url,
    beat_schedule={
        "cleanup-expired-api-keys":   {"task": "tasks.cleanup_expired_api_keys",  "schedule": 1800},
        "archive-old-simulations":    {"task": "tasks.archive_old_simulations",    "schedule": {"hour": 3, "minute": 0}},
        "retry-failed-simulations":   {"task": "tasks.retry_failed_simulations",   "schedule": 900},
        "rollup-daily-metrics":       {"task": "tasks.rollup_daily_metrics",       "schedule": {"hour": 1, "minute": 0}},
        "postgres-vacuum-analyze":    {"task": "tasks.postgres_vacuum_analyze",    "schedule": {"day_of_week": 0, "hour": 4, "minute": 0}},
        "watchdog-stale-sims":        {"task": "tasks.watchdog_stale_sims",        "schedule": 600},
    },
)


@worker_init.connect
def on_worker_init(**kwargs):
    """Initialize DB connections AFTER Celery fork — prevents connection corruption."""
    from db.database import init_db
    from db.mongo import init_mongo
    init_db()
    init_mongo()
    logger.info("Worker DB connections initialized post-fork")
