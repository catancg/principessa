from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.limiter import limiter
from app.db.session import engine
from app.models.base import Base

from app.routers.health import router as health_router
from app.routers.signup import router as signup_router
from app.routers.unsubscribe import router as unsubscribe_router
from app.routers.admin import router as admin_router
from app.routers.admin_dashboard import router as admin_dashboard_router
from app.routers.db_check import router as db_check_router
from app.routers.admin_campaigns import router as admin_campaign_router
from app.routers.admin_api import router as admin_api_router
from app.routers.admin_ui import router as admin_ui_router
from app.routers.meta_webhook import router as meta_webhook_router
from app.routers.admin_variants import router as admin_variants_router
from app.routers.story_builder import router as story_builder_router

Base.metadata.create_all(bind=engine, checkfirst=True)

app = FastAPI(title="Principessa Pastelería — API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(health_router)
app.include_router(signup_router)
app.include_router(unsubscribe_router)
app.include_router(admin_router)
app.include_router(admin_dashboard_router)
app.include_router(db_check_router)
app.include_router(admin_campaign_router)
app.include_router(admin_api_router)
app.include_router(admin_ui_router)
app.include_router(meta_webhook_router)
app.include_router(admin_variants_router)
app.include_router(story_builder_router)



app.mount("/static", StaticFiles(directory="app/static"), name="static")
BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app/assets")), name="static")

_uploads_dir = BASE_DIR / "app" / "static" / "uploads"
_uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")
@app.get("/join")
def join():
    return FileResponse(Path("app/static/join.html"))