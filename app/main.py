from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.exceptions import RequestValidationError
from .database import init_db
from .routers import (
    auth,
    users,
    machines,
    machine_ownership,
    scores,
    claim,
    tournaments,
    qr,
    locations,
    meta,
    pages,
)
import os
import logging

# Initialize database (migrations + tables)
init_db()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Origin")
app.add_middleware(GZipMiddleware, minimum_size=100)


@app.exception_handler(HTTPException)
async def log_http_exception(request: Request, exc: HTTPException):
    logger.warning(
        "HTTP error %s on %s %s: %s",
        exc.status_code,
        request.method,
        request.url.path,
        exc.detail,
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def log_validation_exception(request: Request, exc: RequestValidationError):
    logger.warning(
        "Validation error on %s %s: %s", request.method, request.url.path, exc.errors()
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def log_unhandled_exception(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


# Mount static files for universal links
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

well_known_dir = os.path.join(static_dir, ".well-known")
app.mount("/.well-known", StaticFiles(directory=well_known_dir), name="well-known")


app.include_router(pages.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(machines.router, prefix="/api/v1")
app.include_router(machine_ownership.router, prefix="/api/v1")
app.include_router(scores.router, prefix="/api/v1")
app.include_router(locations.router, prefix="/api/v1")
app.include_router(claim.router)
app.include_router(tournaments.router, prefix="/api/v1")
app.include_router(qr.router)
app.include_router(meta.router, prefix="/api/v1")
