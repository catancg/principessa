
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

    template_path = Path("app/templates/weekly_email.html")

    with open(template_path, "r", encoding="utf-8") as f:
        template_str = f.read()

    html = render_email_template(
        template_str,
        {
            "logo_url": logo_url,
            "maps_url": "https://maps.google.com/?q=Principessa+Pasteleria+Buenos+Aires",
            "whatsapp_url": "https://wa.me/5491178933096",
            "address": "Ciudad de Buenos Aires",
            "hours": "Consultá horarios por Instagram",
            "terms_line": "Válido presentando este email en la pastelería Principessa",
            "instagram_url": "https://instagram.com/principessa.pasteleria",
            "instagram_handle": "@principessa.pasteleria",
            "unsubscribe_url": f"{base_url}/unsubscribe?channel=email&value=test@example.com"
        }
    )

    return HTMLResponse(content=html)