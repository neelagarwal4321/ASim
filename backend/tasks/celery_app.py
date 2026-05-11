from celery import Celery
from config import settings

celery_app = Celery(
    "asim",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["tasks.simulation_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
