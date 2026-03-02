from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

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
app = FastAPI(title="Baby Store Engagement API")

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



app.mount("/static", StaticFiles(directory="app/static"), name="static")
BASE_DIR = Path(__file__).resolve().parent.parent  # ajustá según tu estructura
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app/assets")), name="static")
@app.get("/join")
def join():
    return FileResponse(Path("app/static/join.html"))