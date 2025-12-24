from fastapi import APIRouter

from .games import router as games_router
from .leaderboard import router as leaderboard_router
from .machines import router as machines_router
from .admin import router as admin_router
from .tournaments import router as tournaments_router
from .players import router as players_router
from .ray import router as ray_router

api_router = APIRouter(prefix="/api/v1")


@api_router.get("/")
async def root():
    return {"message": "Origin API is running"}


for router in (
    machines_router,
    players_router,
    games_router,
    leaderboard_router,
    admin_router,
    tournaments_router,
    ray_router,
):
    api_router.include_router(router)
