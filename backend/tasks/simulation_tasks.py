import logging
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.run_full_simulation", bind=True)
def run_full_simulation(self, config_id: str, api_key_redis_key: str) -> dict:
    """Phase 2 stub — will orchestrate rounds via Celery group/chord."""
    logger.info("run_full_simulation: config=%s", config_id)
    return {"config_id": config_id, "status": "stub"}
