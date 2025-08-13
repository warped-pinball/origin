import os
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from ..version import __version__

router = APIRouter(include_in_schema=False)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
API_BASE = os.environ.get("PUBLIC_API_URL", "")


def _render(template_name: str):
    async def render(request: Request):
        return templates.TemplateResponse(request, template_name, {"version": __version__, "api_base": API_BASE})
    return render

PAGE_TEMPLATES = {
    "/": "index.html",
    "/signup": "signup.html",
    "/signup/success": "signup_success.html",
    "/reset-password": "reset_password.html",
    "/privacy": "privacy.html",
    "/terms": "terms.html",
}

for path, template in PAGE_TEMPLATES.items():
    router.get(path, response_class=HTMLResponse)(_render(template))
