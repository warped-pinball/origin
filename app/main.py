from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .database import Base, engine
from .routers import auth, users, machines, scores
from .version import __version__
import os

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pinball Score Tracker")

# Mount static files for universal links
static_dir = os.path.join(os.path.dirname(__file__), 'static/.well-known')
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount('/.well-known', StaticFiles(directory=static_dir), name='static')

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(machines.router)
app.include_router(scores.router)

@app.get("/version")
def get_version():
    return {"version": __version__}

