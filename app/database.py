from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
import os

LATEST_DB_VERSION = 1

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
    version = get_db_version()
    if version < 1:
        insp = inspect(engine)
        if "users" in insp.get_table_names():
            cols = {c["name"] for c in insp.get_columns("users")}
            if "screen_name" not in cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN screen_name VARCHAR"))
        set_db_version(1)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
