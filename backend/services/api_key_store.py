import base64
import logging
import redis
from cryptography.fernet import Fernet
from config import settings

logger = logging.getLogger(__name__)


# Derive a 32-byte Fernet key from SECRET_KEY
def _fernet() -> Fernet:
    raw = settings.secret_key.encode()[:32].ljust(32, b"0")
    key = base64.urlsafe_b64encode(raw)
    return Fernet(key)


def store_api_key(simulation_id: str, api_key: str, ttl_seconds: int = 3600) -> None:
    """Encrypt and store user API key in Redis for simulation duration."""
    r = redis.from_url(settings.redis_url, decode_responses=False)
    token = _fernet().encrypt(api_key.encode())
    r.setex(f"apikey:{simulation_id}", ttl_seconds, token)
    logger.info("Stored encrypted API key for sim %s (TTL=%ds)", simulation_id, ttl_seconds)


def retrieve_api_key(simulation_id: str) -> str | None:
    """Retrieve and decrypt user API key from Redis."""
    r = redis.from_url(settings.redis_url, decode_responses=False)
    token = r.get(f"apikey:{simulation_id}")
    if not token:
        return None
    try:
        return _fernet().decrypt(token).decode()
    except Exception as exc:
        logger.error("Failed to decrypt API key for sim %s: %s", simulation_id, exc)
        return None


def delete_api_key(simulation_id: str) -> None:
    r = redis.from_url(settings.redis_url, decode_responses=False)
    r.delete(f"apikey:{simulation_id}")
