from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import database

from .paths import STATIC_DIR
from .routers import api_router, pages_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_db()
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(api_router)
app.include_router(pages_router)
