from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings


class Base(DeclarativeBase):
    pass


_engine = None
AsyncSessionLocal = None  # set by init_db() — called from worker_init signal


def init_db():
    global _engine, AsyncSessionLocal
    _engine = create_async_engine(
        settings.database_url,
        echo=settings.app_env == "development",
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=0,
    )
    AsyncSessionLocal = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
