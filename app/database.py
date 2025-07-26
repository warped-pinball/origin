from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import re
import importlib.util
from pathlib import Path

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

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db/postgres")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db_version() -> int:
    insp = inspect(engine)
    if "schema_version" not in insp.get_table_names():
        return 0
    with engine.connect() as conn:
        res = conn.execute(text("SELECT version FROM schema_version LIMIT 1"))
        row = res.fetchone()
        return row[0] if row else 0


def set_db_version(version: int) -> None:
    insp = inspect(engine)
    with engine.begin() as conn:
        if "schema_version" not in insp.get_table_names():
            conn.execute(text("CREATE TABLE schema_version (version INTEGER NOT NULL)"))
            conn.execute(text("INSERT INTO schema_version (version) VALUES (:v)"), {"v": version})
        else:
            conn.execute(text("UPDATE schema_version SET version = :v"), {"v": version})


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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
