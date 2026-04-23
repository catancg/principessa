import os
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

router = APIRouter(tags=["story"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")
JOIN_URL = f"{BASE_URL}/join"


def require_builder_key(x_admin_key: str | None = Header(default=None)):
    admin_key   = os.getenv("ADMIN_API_KEY", "")
    builder_key = os.getenv("BUILDER_API_KEY", "")
    valid = {k for k in [admin_key, builder_key] if k}
    if not valid:
        raise HTTPException(status_code=500, detail="No API keys configured")
    if x_admin_key not in valid:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/story-builder", response_class=HTMLResponse)
def story_builder():
    page = jinja_env.get_template("story_builder.html")
    return HTMLResponse(content=page.render(join_url=JOIN_URL))
