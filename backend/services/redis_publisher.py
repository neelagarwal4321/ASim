import json
import logging
import redis
from config import settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def publish_round(simulation_id: str, round_data: dict) -> None:
    """Publish round result to Redis channel pubsub:sim:{id}:rounds."""
    channel = f"pubsub:sim:{simulation_id}:rounds"
    payload = json.dumps(round_data)
    get_redis().publish(channel, payload)
    logger.debug("Published round to %s (%d bytes)", channel, len(payload))
