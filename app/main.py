from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .database import Base, engine, run_migrations
from .routers import auth, users, machines, scores
from .version import __version__
import os

# Run migrations before ensuring all tables exist
run_migrations()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Origin")

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

API_BASE = os.environ.get("PUBLIC_API_URL", "")

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse(request, "index.html", {"version": __version__, "api_base": API_BASE})

# Mount static files for universal links
static_root = os.path.join(os.path.dirname(__file__), 'static')
well_known_dir = os.path.join(static_root, '.well-known')
if not os.path.exists(well_known_dir):
    os.makedirs(well_known_dir, exist_ok=True)
app.mount('/static', StaticFiles(directory=static_root), name='static')
app.mount('/.well-known', StaticFiles(directory=well_known_dir), name='well-known')

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(machines.router, prefix="/api/v1")
app.include_router(scores.router, prefix="/api/v1")

@app.get("/api/v1/version")
def get_version():
    return {"version": __version__}

