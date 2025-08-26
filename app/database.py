from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import time

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
    """Wait for the database to become available."""
    wait_for_db()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
