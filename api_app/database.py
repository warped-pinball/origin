from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Settings(BaseSettings):
    """Application settings sourced from environment variables."""

    DATABASE_URL: str = f"sqlite+aiosqlite:///{Path('./data/app.db').resolve()}"
    LOAD_SAMPLE_DATA: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


def _prepare_sqlite_storage(database_url: str) -> None:
    url = make_url(database_url)
    if url.drivername.startswith("sqlite") and url.database not in (None, "", ":memory:"):
        Path(url.database).expanduser().parent.mkdir(parents=True, exist_ok=True)


_prepare_sqlite_storage(settings.DATABASE_URL)

engine = create_async_engine(settings.DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    if settings.LOAD_SAMPLE_DATA:
        from .sample_data import seed_example_data

        async with AsyncSessionLocal() as session:
            await seed_example_data(session)
