
import os
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

    base_url = str(request.base_url).rstrip("/")
    logo_url = f"{base_url}/static/logo.png"

    template_path = Path("app/templates/pika_pika_weekly.html")

    with open(template_path, "r", encoding="utf-8") as f:
        template_str = f.read()

    html = render_email_template(
        template_str,
        {
            "logo_url": logo_url,
            "maps_url": "https://www.google.com/maps/place/Pika+pika/@-33.0094136,-58.5212939,17z/data=!3m1!4b1!4m6!3m5!1s0x95baa96e7a3c9b9b:0xe3dcf248c61b47ba!8m2!3d-33.0094136!4d-58.5212939!16s%2Fg%2F11s5zh8086?entry=ttu&g_ep=EgoyMDI2MDIyNS4wIKXMDSoASAFQAw%3D%3D",
            "whatsapp_url": "https://wa.me/5493446586123",
            "address": "Rocamora 35, Gualeguaychú, Entre Ríos",
            "hours": "Lun a Sáb",
            "terms_line": "Válido presentando este email en el local Pika Pika",
            "instagram_url": "https://instagram.com/pikapikagchu",
            "instagram_handle": "@pikapikagchu",
            "unsubscribe_url": f"{base_url}/unsubscribe?channel=email&value=test@example.com"
        }
    )

    return HTMLResponse(content=html)