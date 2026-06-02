import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="tasks.cleanup_expired_api_keys")
def cleanup_expired_api_keys():
    pass


@shared_task(name="tasks.archive_old_simulations")
def archive_old_simulations():
    pass


@shared_task(name="tasks.retry_failed_simulations")
def retry_failed_simulations():
    pass


@shared_task(name="tasks.rollup_daily_metrics")
def rollup_daily_metrics():
    pass


@shared_task(name="tasks.postgres_vacuum_analyze")
def postgres_vacuum_analyze():
    pass


@shared_task(name="tasks.watchdog_stale_sims")
def watchdog_stale_sims():
    pass
