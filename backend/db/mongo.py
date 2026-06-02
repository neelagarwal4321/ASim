import logging
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None


def init_mongo():
    global _client
    _client = AsyncIOMotorClient(settings.mongodb_url)
    logger.info("MongoDB client initialized (post-fork)")


def get_mongo_client() -> AsyncIOMotorClient:
    if _client is None:
        # Lazy fallback for non-Celery contexts (FastAPI, tests)
        init_mongo()
    return _client


def get_db():
    return get_mongo_client()[settings.mongodb_db]


def agent_states_col():         return get_db()["agent_states"]
def round_logs_col():           return get_db()["round_logs"]
def community_snapshots_col():  return get_db()["community_snapshots"]
def agent_responses_col():      return get_db()["agent_responses"]
def memory_logs_col():          return get_db()["memory_logs"]
