import asyncio
import logging
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from contextlib import asynccontextmanager

from . import models, schemas, database, udp_listener

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables
models.Base.metadata.create_all(bind=database.engine)

udp_server = udp_listener.UDPListener()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await udp_server.start()
    yield
    # Shutdown
    udp_server.stop()

app = FastAPI(title="Vector Pinball Hub", lifespan=lifespan)

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Welcome to Vector Pinball Hub"}

@app.get("/machines/", response_model=List[schemas.Machine])
def read_machines(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    machines = db.query(models.Machine).offset(skip).limit(limit).all()
    return machines

@app.get("/games/", response_model=List[schemas.Game])
def read_games(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    games = db.query(models.Game).offset(skip).limit(limit).all()
    return games

@app.get("/games/active", response_model=List[schemas.Game])
def read_active_games(db: Session = Depends(get_db)):
    games = db.query(models.Game).filter(models.Game.is_active == True).all()
    return games
