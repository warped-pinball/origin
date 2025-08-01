from sqlalchemy import create_engine, inspect, text, exc
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import re
import importlib.util
from pathlib import Path
import time

# Migrations live in app/migrations as numbered Python files. The highest
# numbered file represents the latest schema version.
MIGRATIONS_DIR = Path(__file__).parent / "migrations"
MIGRATIONS = {}
for fp in MIGRATIONS_DIR.glob("*.py"):
    m = re.match(r"(\d+)", fp.stem)
    if m:
        MIGRATIONS[int(m.group(1))] = fp

# Update this constant when adding a new migration
EXPECTED_DB_VERSION = max(MIGRATIONS.keys(), default=0)

# Build DATABASE_URL from individual settings if not provided
if "DATABASE_URL" in os.environ:
    DATABASE_URL = os.environ["DATABASE_URL"]
else:
    db_user = os.getenv("POSTGRES_USER", "postgres")
    db_password = os.getenv("POSTGRES_PASSWORD", "postgres")
    db_host = os.getenv("POSTGRES_HOST", "db")
    db_name = os.getenv("POSTGRES_DB", "postgres")
    DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}/{db_name}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db_version() -> int:
    """Return the current schema version or 0 if the version table is absent."""
    with engine.connect() as conn:
        try:
            res = conn.execute(text("SELECT version FROM schema_version LIMIT 1"))
        except exc.SQLAlchemyError:
            return 0
        row = res.fetchone()
        return row[0] if row else 0


def set_db_version(version: int) -> None:
    """Create the version table if needed and record the provided version."""
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"))
        conn.execute(text("DELETE FROM schema_version"))
        conn.execute(text("INSERT INTO schema_version (version) VALUES (:v)"), {"v": version})


def run_migrations() -> None:
    current = get_db_version()
    for target_version in range(current + 1, EXPECTED_DB_VERSION + 1):
        path = MIGRATIONS.get(target_version)
        if not path:
            continue
        spec = importlib.util.spec_from_file_location(f"migration_{target_version}", path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        if hasattr(mod, "upgrade"):
            mod.upgrade(engine)
        set_db_version(target_version)


def wait_for_db(max_attempts: int = 10, delay: float = 1.0) -> None:
    """Attempt to connect to the database until successful or out of retries."""
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect():
                return
        except exc.OperationalError:
            if attempt == max_attempts:
                raise
            time.sleep(delay)


def init_db() -> None:
    """Wait for DB, run migrations and ensure all tables exist."""
    wait_for_db()
    run_migrations()
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
