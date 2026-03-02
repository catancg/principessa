from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.jobs.weekly_scheduler import queue_weekly_promo
from app.services.email_renderer import render_email_template
from pathlib import Path
router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/queue-weekly")
def admin_queue_weekly(db: Session = Depends(get_db)):
    return queue_weekly_promo(db)





router = APIRouter()


@router.get("/admin/preview-email", response_class=HTMLResponse)
def preview_email(request: Request):

    # Construimos BASE_URL dinámicamente
    base_url = str(request.base_url).rstrip("/")

    logo_url = f"{base_url}/static/logo.png"

    template_path = Path("app/templates/pika_pika_weekly.html")

    with open(template_path, "r", encoding="utf-8") as f:
        template_str = f.read()

    html = render_email_template(
        template_str,
        {
            "name": "Carlos",
            "interest": "toys",
            "cta_link": "https://pikapika.com",
            "unsubscribe_link": "#",
            "logo_url": logo_url,   # 👈 agregado
        }
    )

    return HTMLResponse(content=html)