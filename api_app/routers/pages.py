from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse

from ..paths import STATIC_HTML_DIR

pages_router = APIRouter()


@pages_router.get("/register", response_class=FileResponse)
async def serve_registration_page():
    return FileResponse(STATIC_HTML_DIR / "registration.html")


@pages_router.get("/big-screen", response_class=FileResponse)
async def serve_big_screen_page():
    return FileResponse(STATIC_HTML_DIR / "big-screen.html")


@pages_router.get("/players", response_class=FileResponse)
async def serve_player_roster_page():
    return FileResponse(STATIC_HTML_DIR / "players.html")


@pages_router.get("/players/{player_id}", response_class=FileResponse)
async def serve_player_page(player_id: int):
    return FileResponse(STATIC_HTML_DIR / "player.html")


@pages_router.get("/admin", response_class=FileResponse)
async def serve_admin_page():
    return FileResponse(STATIC_HTML_DIR / "admin.html")


@pages_router.get("/admin/machines/{machine_slug}", response_class=FileResponse)
async def serve_admin_machine_page(machine_slug: str):
    return FileResponse(STATIC_HTML_DIR / "admin-machine.html")


@pages_router.get("/admin/tournaments/new", response_class=FileResponse)
async def serve_admin_tournament_create_page():
    return FileResponse(STATIC_HTML_DIR / "admin-tournament.html")


@pages_router.get("/admin/tournaments/{tournament_id}", response_class=FileResponse)
async def serve_admin_tournament_edit_page(tournament_id: int):
    return FileResponse(STATIC_HTML_DIR / "admin-tournament.html")


@pages_router.get("/brand-guide", response_class=FileResponse)
async def serve_brand_guide_page():
    return FileResponse(STATIC_HTML_DIR / "brand-guide.html")


@pages_router.get("/component-guide", response_class=FileResponse)
async def serve_component_guide_page():
    return FileResponse(STATIC_HTML_DIR / "component-guide.html")


@pages_router.get("/", include_in_schema=False)
async def redirect_to_home():
    return RedirectResponse(url="/register")


@pages_router.get("/{full_path:path}", include_in_schema=False)
async def redirect_unknown_paths(full_path: str, request: Request):
    if request.url.path.startswith("/api/"):
        raise HTTPException(status_code=404, detail="Not found")

    return RedirectResponse(url="/register")
