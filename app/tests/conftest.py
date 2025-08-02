import os
import importlib
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from scripts.generate_schema_md import main as generate_schema_md

# Automatically refresh the schema documentation before tests execute
generate_schema_md()

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
os.environ["DATABASE_URL"] = SQLALCHEMY_DATABASE_URL
if os.path.exists("test.db"):
    os.remove("test.db")

# Ensure ORM modules use the test database after schema generation
import app.database as database
importlib.reload(database)
import app.models as models
importlib.reload(models)

from ..main import app
from ..websocket_app import app as ws_app
from ..database import Base, get_db

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
ws_app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db_session():
    with TestingSessionLocal() as session:
        yield session

@pytest.fixture
def ws_client():
    return TestClient(ws_app)
