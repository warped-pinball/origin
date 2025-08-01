from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.gzip import GZipMiddleware
from .database import init_db
from .routers import auth, users, machines, scores, claim
from .version import __version__
import os

# Initialize database (migrations + tables)
init_db()

app = FastAPI(title="Origin")
app.add_middleware(GZipMiddleware, minimum_size=100)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

API_BASE = os.environ.get("PUBLIC_API_URL", "")

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse(request, "index.html", {"version": __version__, "api_base": API_BASE})

# Mount static files for universal links
static_dir = os.path.join(os.path.dirname(__file__), 'static')
app.mount("/static", StaticFiles(directory=static_dir), name='static')

well_known_dir = os.path.join(static_dir, '.well-known')
app.mount('/.well-known', StaticFiles(directory=well_known_dir), name='well-known')


app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(machines.router, prefix="/api/v1")
app.include_router(scores.router, prefix="/api/v1")
app.include_router(claim.router)

@app.get("/api/v1/version")
def get_version():
    return {"version": __version__}

