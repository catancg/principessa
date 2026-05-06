import os
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(tags=["birthday-builder"])

BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")
WHATSAPP_URL = "https://wa.me/5491178933096"
INSTAGRAM_URL = "https://instagram.com/principessa.pasteleria"
INSTAGRAM_HANDLE = "@principessa.pasteleria"

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

_SUPABASE_BUCKET = "promo-images"
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_IMAGE_BYTES = 5 * 1024 * 1024


def require_builder_key(x_admin_key: str | None = Header(default=None)):
    valid = {k for k in [os.getenv("ADMIN_API_KEY", ""), os.getenv("BUILDER_API_KEY", "")] if k}
    if not valid:
        raise HTTPException(status_code=500, detail="No API keys configured")
    if x_admin_key not in valid:
        raise HTTPException(status_code=401, detail="Unauthorized")


async def _upload_image(content: bytes, filename: str, content_type: str) -> str:
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    if supabase_url and service_key and "your_service_role_key" not in service_key:
        ext = Path(filename).suffix.lower() if filename else ".jpg"
        safe_name = f"{uuid.uuid4().hex}{ext}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{supabase_url}/storage/v1/object/{_SUPABASE_BUCKET}/{safe_name}",
                content=content,
                headers={"Authorization": f"Bearer {service_key}", "Content-Type": content_type},
            )
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail=f"Supabase upload failed: {resp.text[:400]}")
        return f"{supabase_url}/storage/v1/object/public/{_SUPABASE_BUCKET}/{safe_name}"

    uploads_dir = TEMPLATES_DIR.parent / "static" / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix.lower() if filename else ".jpg"
    local_name = f"{uuid.uuid4().hex}{ext}"
    (uploads_dir / local_name).write_bytes(content)
    return f"/uploads/{local_name}"


@router.get("/admin/birthday-builder", response_class=HTMLResponse)
def birthday_builder_page():
    return HTMLResponse(content=jinja_env.get_template("birthday_builder.html").render())


@router.get("/admin/birthday-builder/config", dependencies=[Depends(require_builder_key)])
def birthday_builder_config(db: Session = Depends(get_db)):
    row = db.execute(
        text("SELECT promo_code, promo_text, image_url, discount_text FROM birthday_campaign_config WHERE id = 1")
    ).mappings().first()
    if not row:
        return {"promo_code": None, "promo_text": None, "image_url": None, "discount_text": "10% de descuento"}
    return dict(row)


@router.post("/admin/birthday-builder/render", response_class=Response, dependencies=[Depends(require_builder_key)])
def birthday_builder_render(
    promo_code:    str = Form(default=""),
    promo_text:    str = Form(default=""),
    image_url:     str = Form(default=""),
    discount_text: str = Form(default="10% de descuento"),
):
    html = jinja_env.get_template("birthday_email.html").render(
        name="María",
        logo_url=f"{BASE_URL}/static/logo_cream.png?v=2",
        whatsapp_url=WHATSAPP_URL,
        instagram_url=INSTAGRAM_URL,
        instagram_handle=INSTAGRAM_HANDLE,
        unsubscribe_url="#",
        promo_code=promo_code.strip() or None,
        promo_text=promo_text.strip() or None,
        image_url=image_url.strip() or None,
        discount_text=discount_text.strip() or "10% de descuento",
    )
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.post("/admin/birthday-builder/save", dependencies=[Depends(require_builder_key)])
def birthday_builder_save(
    promo_code:    str = Form(default=""),
    promo_text:    str = Form(default=""),
    image_url:     str = Form(default=""),
    discount_text: str = Form(default="10% de descuento"),
    db: Session = Depends(get_db),
):
    db.execute(text("""
        INSERT INTO birthday_campaign_config (id, promo_code, promo_text, image_url, discount_text, updated_at)
        VALUES (1, :promo_code, :promo_text, :image_url, :discount_text, now())
        ON CONFLICT (id) DO UPDATE
            SET promo_code    = EXCLUDED.promo_code,
                promo_text    = EXCLUDED.promo_text,
                image_url     = EXCLUDED.image_url,
                discount_text = EXCLUDED.discount_text,
                updated_at    = now()
    """), {
        "promo_code":    promo_code.strip() or None,
        "promo_text":    promo_text.strip() or None,
        "image_url":     image_url.strip() or None,
        "discount_text": discount_text.strip() or "10% de descuento",
    })
    db.commit()
    return {"ok": True}


@router.post("/admin/birthday-builder/upload-image", dependencies=[Depends(require_builder_key)])
async def birthday_upload_image(file: UploadFile = File(...)):
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo no soportado: '{file.content_type}'.")
    content = await file.read()
    if len(content) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Imagen demasiado grande (máx 5 MB).")
    url = await _upload_image(content, file.filename or "image.jpg", file.content_type)
    return {"url": url}
