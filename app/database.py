from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import re
from pathlib import Path

# Migrations live in app/migrations as numbered SQL files. The highest
# numbered file represents the latest schema version.
MIGRATIONS_DIR = Path(__file__).parent / "migrations"
MIGRATIONS = {}
for fp in MIGRATIONS_DIR.glob("*.sql"):
    m = re.match(r"(\d+)", fp.stem)
    if m:
        MIGRATIONS[int(m.group(1))] = fp
LATEST_DB_VERSION = max(MIGRATIONS.keys(), default=0)

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
    insp = inspect(engine)
    for target_version in sorted(MIGRATIONS.keys()):
        if target_version <= current:
            continue

        # Example introspection for the first migration so new databases are not
        # altered twice when the column already exists.
        if target_version == 1:
            if "users" in insp.get_table_names():
                cols = {c["name"] for c in insp.get_columns("users")}
                if "screen_name" in cols:
                    set_db_version(target_version)
                    current = target_version
                    continue

        path = MIGRATIONS[target_version]
        with open(path) as f:
            sql = f.read()
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
        set_db_version(target_version)
        current = target_version

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
