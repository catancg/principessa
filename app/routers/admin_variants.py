import os
import smtplib
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Form, Query, UploadFile, File
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.email_variant import EmailVariant
from app.models.send_approval import SendApproval
from app.services.ai_copy_service import generate_variants

router = APIRouter(tags=["variants"])

BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")
APPROVAL_NOTIFY_EMAIL = "catan.994@gmail.com"
NUM_VARIANTS = 2

MAPS_URL = "https://www.google.com/maps/place/Pika+pika/@-33.0094136,-58.5212939,17z"
WHATSAPP_URL = "https://wa.me/5493446586123"
INSTAGRAM_URL = "https://instagram.com/pikapikagchu"
INSTAGRAM_HANDLE = "@pikapikagchu"
ADDRESS = "Rocamora 35, Gualeguaychu, Entre Rios"
HOURS = "Lunes a Sabado"
TERMS_LINE = "Válido presentando este email en el local Pika Pika"

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


# ── helpers ──────────────────────────────────────────────────────────────────

def require_admin_key(x_admin_key: str | None = Header(default=None)):
    expected = os.getenv("ADMIN_API_KEY")
    if not expected:
        raise HTTPException(status_code=500, detail="ADMIN_API_KEY not set")
    if x_admin_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def require_builder_key(x_admin_key: str | None = Header(default=None)):
    """Accepts either ADMIN_API_KEY or BUILDER_API_KEY."""
    admin_key = os.getenv("ADMIN_API_KEY", "")
    builder_key = os.getenv("BUILDER_API_KEY", "")
    valid = {k for k in [admin_key, builder_key] if k}
    if not valid:
        raise HTTPException(status_code=500, detail="No API keys configured")
    if x_admin_key not in valid:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _render_variant_email_html(variant: EmailVariant, to_email: str = "preview@example.com") -> str:
    base_url = BASE_URL.rstrip("/")
    template = jinja_env.get_template("ai_variant_email.html")
    return template.render(
        logo_url=f"{base_url}/static/logo.png",
        # AI gaps
        headline=variant.headline,
        highlight_phrase=variant.highlight_phrase,
        body_intro=variant.body_intro,
        block_1_emoji=variant.block_1_emoji,
        block_1_title=variant.block_1_title,
        block_1_text=variant.block_1_text,
        block_2_emoji=variant.block_2_emoji,
        block_2_title=variant.block_2_title,
        block_2_text=variant.block_2_text,
        closing_message=variant.closing_message,
        # fixed system values
        terms_line=TERMS_LINE,
        maps_url=MAPS_URL,
        whatsapp_url=WHATSAPP_URL,
        address=ADDRESS,
        hours=HOURS,
        instagram_url=INSTAGRAM_URL,
        instagram_handle=INSTAGRAM_HANDLE,
        unsubscribe_url=f"{base_url}/unsubscribe?channel=email&value={to_email}",
    )


def _send_approval_notification(variants: list[EmailVariant]):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    from_name = os.getenv("SMTP_FROM_NAME", "Pika Pika")
    from_email = os.getenv("SMTP_FROM_EMAIL")

    if not all([smtp_host, smtp_user, smtp_pass, from_email]):
        print("WARN: SMTP not configured, skipping approval notification")
        return

    base = BASE_URL.rstrip("/")
    links_text = "\n".join(
        f"  Variante {v.variant_index}: {base}/variants/{v.approval_token}/preview"
        for v in variants
    )
    links_html = "".join(
        f'<p style="margin:8px 0;">'
        f'<a href="{base}/variants/{v.approval_token}/preview" '
        f'style="color:#FF7A3D;font-weight:bold;font-size:15px;">Ver Variante {v.variant_index} — "{v.subject_line}" →</a>'
        f'</p>'
        for v in variants
    )

    text_body = (
        f"Hola!\n\n"
        f"Se generaron {NUM_VARIANTS} variantes de email para la campaña semanal de Pika Pika.\n\n"
        f"Revisalas y aprobá la que más te guste:\n{links_text}\n\n"
        f"Una vez que apruebes una, confirmá el envío desde el panel de admin.\n"
    )
    html_body = f"""
    <div style="font-family:'Nunito',Arial,sans-serif;max-width:520px;margin:0 auto;padding:32px 24px;background:#F7FFF5;">
      <div style="background:#fff;border-radius:20px;padding:32px;box-shadow:0 2px 12px rgba(0,0,0,.06);">
        <h2 style="color:#5B8C5A;font-size:22px;margin:0 0 8px;">Nuevas variantes de email</h2>
        <p style="color:#555;font-size:14px;margin:0 0 24px;">
          Se generaron <strong>{NUM_VARIANTS} variantes</strong> para la campaña semanal.<br>
          Hacé clic en cada una para ver la vista previa y decidir.
        </p>
        <div style="background:#F7FFF5;border-radius:12px;padding:16px 20px;">
          {links_html}
        </div>
        <hr style="margin:24px 0;border:none;border-top:1px solid #e5e7eb;">
        <p style="font-size:12px;color:#9ca3af;margin:0;">
          Una vez aprobada, un administrador confirmará el envío a los clientes desde el panel.
        </p>
      </div>
    </div>
    """

    msg = EmailMessage()
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = APPROVAL_NOTIFY_EMAIL
    msg["Subject"] = f"[Pika Pika] Revisá las {NUM_VARIANTS} variantes de email"
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


# ── endpoints ─────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str = ""
    campaign_type: str = "weekly_promo"


_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_UPLOADS_DIR = TEMPLATES_DIR.parent / "static" / "uploads"
_SUPABASE_BUCKET = "email-images"
_MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


async def _save_image(content: bytes, filename: str, content_type: str) -> str:
    """Upload to Supabase Storage if configured, otherwise fall back to local disk."""
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    service_key  = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    if supabase_url and service_key and "your_service_role_key" not in service_key:
        ext = Path(filename).suffix.lower() if filename else ".jpg"
        safe_name = f"{uuid.uuid4().hex}{ext}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{supabase_url}/storage/v1/object/{_SUPABASE_BUCKET}/{safe_name}",
                content=content,
                headers={
                    "Authorization": f"Bearer {service_key}",
                    "Content-Type": content_type,
                },
            )
        print(f"[upload] Supabase response: {resp.status_code} | {resp.text[:500]}")
        if resp.status_code not in (200, 201):
            raise HTTPException(
                status_code=500,
                detail=f"Supabase upload failed (HTTP {resp.status_code}): {resp.text[:400]}",
            )
        return f"{supabase_url}/storage/v1/object/public/{_SUPABASE_BUCKET}/{safe_name}"

    # fallback: local disk (works for builder preview, not for email delivery)
    _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix.lower() if filename else ".jpg"
    local_name = f"{uuid.uuid4().hex}{ext}"
    (_UPLOADS_DIR / local_name).write_bytes(content)
    return f"/uploads/{local_name}"


@router.post("/admin/email-builder/upload-image", dependencies=[Depends(require_builder_key)])
async def upload_image(file: UploadFile = File(...)):
    """Upload a promo image to Supabase Storage; returns its public URL."""
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported type '{file.content_type}'. Use JPEG, PNG, WEBP or GIF.")

    content = await file.read()
    if len(content) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Image too large (max 5 MB).")

    url = await _save_image(content, file.filename or "image.jpg", file.content_type)
    return {"url": url}


@router.get("/builder-login", response_class=HTMLResponse)
def builder_login():
    page = jinja_env.get_template("builder_login.html")
    return HTMLResponse(content=page.render())


@router.get("/admin/email-builder", response_class=HTMLResponse)
def email_builder():
    page = jinja_env.get_template("email_builder.html")
    return HTMLResponse(content=page.render())


@router.post("/admin/email-builder/render", response_class=Response, dependencies=[Depends(require_builder_key)])
def email_builder_render(
    subject_line:     str = Form(default=""),
    preview_text:     str = Form(default=""),
    headline:         str = Form(default=""),
    highlight_phrase: str = Form(default=""),
    body_intro:       str = Form(default=""),
    block_1_emoji:    str = Form(default=""),
    block_1_title:    str = Form(default=""),
    block_1_text:     str = Form(default=""),
    block_2_emoji:    str = Form(default=""),
    block_2_title:    str = Form(default=""),
    block_2_text:     str = Form(default=""),
    closing_message:  str = Form(default=""),
    promo_image_url:  str = Form(default=""),
):
    """Render ai_variant_email.html with the posted form values and return raw HTML."""
    base_url = BASE_URL.rstrip("/")
    image_url = (base_url + promo_image_url) if promo_image_url.startswith("/") else promo_image_url
    template = jinja_env.get_template("ai_variant_email.html")
    html = template.render(
        logo_url          = f"{base_url}/static/logo.png",
        headline          = headline,
        highlight_phrase  = highlight_phrase,
        body_intro        = body_intro,
        block_1_emoji     = block_1_emoji,
        block_1_title     = block_1_title,
        block_1_text      = block_1_text,
        block_2_emoji     = block_2_emoji,
        block_2_title     = block_2_title,
        block_2_text      = block_2_text,
        closing_message   = closing_message,
        promo_image_url   = image_url or None,
        terms_line        = TERMS_LINE,
        maps_url          = MAPS_URL,
        whatsapp_url      = WHATSAPP_URL,
        address           = ADDRESS,
        hours             = HOURS,
        instagram_url     = INSTAGRAM_URL,
        instagram_handle  = INSTAGRAM_HANDLE,
        unsubscribe_url   = "#",
    )
    return Response(content=html, media_type="text/html; charset=utf-8")


def _form_fields():
    """Shared Form declarations for builder endpoints."""
    return {}  # placeholder — fields are declared per-endpoint


def _render_builder_email(fields: dict, to_email: str = "#") -> tuple[str, str, str]:
    """Returns (subject, text_body, html_body) from raw form field dict."""
    base_url = BASE_URL.rstrip("/")
    subject   = fields.get("subject_line") or "Novedades de Pika Pika"
    headline  = fields.get("headline", "")
    hp        = fields.get("highlight_phrase", "")
    bi        = fields.get("body_intro", "")
    closing   = fields.get("closing_message", "")
    unsubscribe_url = f"{base_url}/unsubscribe?channel=email&value={to_email}" if to_email != "#" else "#"

    raw_img = fields.get("promo_image_url", "").strip()
    image_url = (base_url + raw_img) if raw_img.startswith("/") else raw_img

    text_body = f"{headline}\n\n{hp}\n\n{bi}\n\n{closing}\n\nDarte de baja:\n{unsubscribe_url}\n"
    html_body = jinja_env.get_template("ai_variant_email.html").render(
        logo_url         = f"{base_url}/static/logo.png",
        headline         = headline,
        highlight_phrase = hp,
        body_intro       = bi,
        block_1_emoji    = fields.get("block_1_emoji", ""),
        block_1_title    = fields.get("block_1_title", ""),
        block_1_text     = fields.get("block_1_text", ""),
        block_2_emoji    = fields.get("block_2_emoji", ""),
        block_2_title    = fields.get("block_2_title", ""),
        block_2_text     = fields.get("block_2_text", ""),
        closing_message  = closing,
        promo_image_url  = image_url or None,
        terms_line       = TERMS_LINE,
        maps_url         = MAPS_URL,
        whatsapp_url     = WHATSAPP_URL,
        address          = ADDRESS,
        hours            = HOURS,
        instagram_url    = INSTAGRAM_URL,
        instagram_handle = INSTAGRAM_HANDLE,
        unsubscribe_url  = unsubscribe_url,
    )
    return subject, text_body, html_body


def _smtp_send(to_email: str, subject: str, text_body: str, html_body: str):
    host      = os.getenv("SMTP_HOST")
    port      = int(os.getenv("SMTP_PORT", "587"))
    user      = os.getenv("SMTP_USERNAME")
    password  = os.getenv("SMTP_PASSWORD")
    from_name = os.getenv("SMTP_FROM_NAME", "Pika Pika")
    from_addr = os.getenv("SMTP_FROM_EMAIL")

    msg = EmailMessage()
    msg["From"]    = f"{from_name} <{from_addr}>"
    msg["To"]      = to_email
    msg["Subject"] = subject
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(host, port, timeout=20) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)


def _send_approval_notification_send(queued_count: int, subject_preview: str, approve_url: str, cancel_url: str):
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:24px;">
      <h2 style="color:#111;">Aprobación de envío — Pika Pika</h2>
      <p style="color:#555;">Se solicitó enviar <strong>{queued_count} emails</strong>.</p>
      <p style="color:#555;">Asunto: <em>{subject_preview}</em></p>
      <div style="margin:28px 0;display:flex;gap:12px;">
        <a href="{approve_url}" style="background:#16a34a;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:700;">✓ Aprobar envío</a>
        <a href="{cancel_url}" style="background:#dc2626;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:700;">✕ Cancelar</a>
      </div>
      <p style="color:#9ca3af;font-size:12px;">Este link expira una vez usado.</p>
    </div>
    """
    _smtp_send(
        APPROVAL_NOTIFY_EMAIL,
        f"⚠️ Aprobar envío de {queued_count} emails — Pika Pika",
        f"Aprobar: {approve_url}\nCancelar: {cancel_url}",
        html,
    )


@router.post("/admin/email-builder/queue", dependencies=[Depends(require_builder_key)])
def builder_queue(
    subject_line:     str = Form(default=""),
    preview_text:     str = Form(default=""),
    headline:         str = Form(default=""),
    highlight_phrase: str = Form(default=""),
    body_intro:       str = Form(default=""),
    block_1_emoji:    str = Form(default=""),
    block_1_title:    str = Form(default=""),
    block_1_text:     str = Form(default=""),
    block_2_emoji:    str = Form(default=""),
    block_2_title:    str = Form(default=""),
    block_2_text:     str = Form(default=""),
    closing_message:  str = Form(default=""),
    promo_image_url:  str = Form(default=""),
    db: Session = Depends(get_db),
):
    """Queue the current builder email to all eligible customers."""
    batch_id = str(uuid.uuid4())
    fields = dict(
        subject_line=subject_line, preview_text=preview_text,
        headline=headline, highlight_phrase=highlight_phrase, body_intro=body_intro,
        block_1_emoji=block_1_emoji, block_1_title=block_1_title, block_1_text=block_1_text,
        block_2_emoji=block_2_emoji, block_2_title=block_2_title, block_2_text=block_2_text,
        closing_message=closing_message, promo_image_url=promo_image_url,
    )

    result = db.execute(text("""
        INSERT INTO message_outbox (
            id, customer_id, to_identity_id, template_key, channel, payload, status, scheduled_for, created_at
        )
        SELECT
            gen_random_uuid(),
            ci.customer_id,
            ci.id,
            'ai_variant_v1',
            'email',
            CAST(:payload AS jsonb),
            'queued',
            now(),
            now()
        FROM customer_identities ci
        JOIN (
            SELECT DISTINCT ON (c2.customer_id) c2.customer_id, c2.status
            FROM consents c2
            WHERE c2.channel = 'email' AND c2.purpose = 'promotions'
            ORDER BY c2.customer_id, c2.created_at DESC
        ) latest ON latest.customer_id = ci.customer_id
        WHERE ci.channel = 'email'
          AND latest.status = 'granted'
          AND NOT EXISTS (
              SELECT 1 FROM message_outbox mo2
              WHERE mo2.to_identity_id = ci.id
                AND (mo2.payload->>'batch_id') = :batch_id
          )
    """), {
        "batch_id": batch_id,
        "payload": __import__("json").dumps({**fields, "batch_id": batch_id}),
    })

    db.commit()
    return {"queued": result.rowcount, "batch_id": batch_id}


@router.delete("/admin/email-builder/clear-queue", dependencies=[Depends(require_builder_key)])
def builder_clear_queue(db: Session = Depends(get_db)):
    result = db.execute(text("""
        DELETE FROM message_outbox
        WHERE status = 'queued'
          AND template_key = 'ai_variant_v1'
          AND channel = 'email'
    """))
    db.commit()
    return {"deleted": result.rowcount}


@router.post("/admin/email-builder/send-queued", dependencies=[Depends(require_builder_key)])
def builder_send_queued(db: Session = Depends(get_db)):
    """Send all queued ai_variant_v1 outbox items now."""
    mode       = os.getenv("EMAIL_SEND_MODE", "TEST").upper()
    test_to    = os.getenv("TEST_TO_EMAIL", "").strip()
    smtp_ready = all(os.getenv(k) for k in ["SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM_EMAIL"])

    if mode != "DRY_RUN" and not smtp_ready:
        raise HTTPException(status_code=500, detail="SMTP not configured")

    rows = db.execute(text("""
        SELECT mo.id, ci.value AS to_email, mo.payload
        FROM message_outbox mo
        JOIN customer_identities ci ON ci.id = mo.to_identity_id
        WHERE mo.status = 'queued'
          AND mo.template_key = 'ai_variant_v1'
          AND mo.channel = 'email'
          AND mo.scheduled_for <= now()
        ORDER BY mo.created_at
        FOR UPDATE SKIP LOCKED
    """)).fetchall()

    sent_ids, failed_ids, errors = [], [], []

    for outbox_id, original_to, payload in rows:
        fields = dict(payload or {})
        fields["email"] = original_to
        try:
            subject, text_body, html_body = _render_builder_email(fields, to_email=original_to)

            if mode == "DRY_RUN":
                print(f"DRY_RUN would send {outbox_id} -> {original_to}")
                sent_ids.append(outbox_id)
                continue

            to_addr = test_to if mode == "TEST" and test_to else original_to
            if mode == "TEST":
                subject   = f"[TEST] {subject}"
                text_body = f"MODO PRUEBA — original: {original_to}\n\n{text_body}"
                html_body = (
                    f"<div style='padding:8px;background:#fff3cd;font-size:12px;'>"
                    f"MODO PRUEBA — original: {original_to}</div>" + html_body
                )

            _smtp_send(to_addr, subject, text_body, html_body)
            sent_ids.append(outbox_id)

        except Exception as e:
            failed_ids.append(outbox_id)
            errors.append({"id": str(outbox_id), "to": original_to, "error": repr(e)})

    if sent_ids:
        db.execute(text("UPDATE message_outbox SET status='sent', sent_at=now() WHERE id = ANY(:ids)"),
                   {"ids": sent_ids})
    if failed_ids:
        db.execute(text("UPDATE message_outbox SET status='failed' WHERE id = ANY(:ids)"),
                   {"ids": failed_ids})

    db.commit()
    return {"sent": len(sent_ids), "failed": len(failed_ids), "mode": mode, "errors": errors}


@router.get("/admin/email-builder/eligible-count", dependencies=[Depends(require_builder_key)])
def eligible_count(db: Session = Depends(get_db)):
    """Return the number of customers eligible to receive the next email."""
    row = db.execute(text("""
        SELECT COUNT(*) AS n
        FROM customer_identities ci
        JOIN v_current_promotions_consent vpc
          ON vpc.customer_id = ci.customer_id AND vpc.channel = 'email'
        WHERE ci.channel = 'email'
          AND vpc.status = 'granted'
    """)).first()
    return {"count": row.n if row else 0}


@router.post("/admin/email-builder/request-send-approval", dependencies=[Depends(require_builder_key)])
def request_send_approval(db: Session = Depends(get_db)):
    """Create a send approval record and email the admin an approve/cancel link."""
    queued_row = db.execute(text("""
        SELECT COUNT(*) AS n, MIN(payload->>'subject_line') AS subject
        FROM message_outbox
        WHERE status = 'queued'
          AND template_key = 'ai_variant_v1'
          AND channel = 'email'
          AND scheduled_for <= now()
    """)).first()

    queued_count = queued_row.n if queued_row else 0
    subject_preview = (queued_row.subject or "Sin asunto") if queued_row else "Sin asunto"

    approval = SendApproval(
        token=uuid.uuid4(),
        status="pending",
        queued_count=queued_count,
        subject_preview=subject_preview,
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)

    base = BASE_URL.rstrip("/")
    approve_url = f"{base}/admin/email-builder/send-approval/{approval.token}/approve"
    cancel_url  = f"{base}/admin/email-builder/send-approval/{approval.token}/cancel"

    _send_approval_notification_send(
        queued_count=queued_count,
        subject_preview=subject_preview,
        approve_url=approve_url,
        cancel_url=cancel_url,
    )

    return {"status": "approval_sent", "count": queued_count}


@router.get("/admin/email-builder/send-approval/{token}/approve", response_class=HTMLResponse)
def approve_send(token: str, db: Session = Depends(get_db)):
    approval = db.query(SendApproval).filter_by(token=token, status="pending").first()
    if not approval:
        return HTMLResponse("<h2>Este link ya fue usado o no es válido.</h2>", status_code=410)

    approval.status = "approved"
    approval.decided_at = datetime.now(timezone.utc)
    db.commit()

    # trigger the actual send
    mode    = os.getenv("EMAIL_SEND_MODE", "TEST").upper()
    test_to = os.getenv("TEST_TO_EMAIL", "").strip()

    rows = db.execute(text("""
        SELECT mo.id, ci.value AS to_email, mo.payload
        FROM message_outbox mo
        JOIN customer_identities ci ON ci.id = mo.to_identity_id
        WHERE mo.status = 'queued'
          AND mo.template_key = 'ai_variant_v1'
          AND mo.channel = 'email'
          AND mo.scheduled_for <= now()
        ORDER BY mo.created_at
        FOR UPDATE SKIP LOCKED
    """)).fetchall()

    sent_ids, failed_ids = [], []
    for outbox_id, original_to, payload in rows:
        fields = dict(payload or {})
        fields["email"] = original_to
        try:
            subject, text_body, html_body = _render_builder_email(fields, to_email=original_to)
            if mode == "DRY_RUN":
                sent_ids.append(outbox_id)
                continue
            to_addr = test_to if mode == "TEST" and test_to else original_to
            if mode == "TEST":
                subject   = f"[TEST] {subject}"
                text_body = f"MODO PRUEBA — original: {original_to}\n\n{text_body}"
                html_body = (f"<div style='padding:8px;background:#fff3cd;font-size:12px;'>"
                             f"MODO PRUEBA — original: {original_to}</div>" + html_body)
            _smtp_send(to_addr, subject, text_body, html_body)
            sent_ids.append(outbox_id)
        except Exception:
            failed_ids.append(outbox_id)

    if sent_ids:
        db.execute(text("UPDATE message_outbox SET status='sent', sent_at=now() WHERE id = ANY(:ids)"),
                   {"ids": sent_ids})
    if failed_ids:
        db.execute(text("UPDATE message_outbox SET status='failed' WHERE id = ANY(:ids)"),
                   {"ids": failed_ids})

    db.commit()

    page = jinja_env.get_template("send_approval.html")
    return HTMLResponse(page.render(action="approved", sent=len(sent_ids), failed=len(failed_ids)))


@router.get("/admin/email-builder/send-approval/{token}/cancel", response_class=HTMLResponse)
def cancel_send(token: str, db: Session = Depends(get_db)):
    approval = db.query(SendApproval).filter_by(token=token, status="pending").first()
    if not approval:
        return HTMLResponse("<h2>Este link ya fue usado o no es válido.</h2>", status_code=410)

    approval.status = "cancelled"
    approval.decided_at = datetime.now(timezone.utc)
    db.commit()

    page = jinja_env.get_template("send_approval.html")
    return HTMLResponse(page.render(action="cancelled", sent=0, failed=0))


@router.post("/admin/generate-variants", dependencies=[Depends(require_admin_key)])
def generate_email_variants(body: GenerateRequest, db: Session = Depends(get_db)):
    """Generate 2 AI email variants and send approval links to the business owner."""
    generation_id = uuid.uuid4()

    raw_variants = generate_variants(prompt=body.prompt, num_variants=NUM_VARIANTS)

    saved: list[EmailVariant] = []
    for i, v in enumerate(raw_variants, start=1):
        variant = EmailVariant(
            id=uuid.uuid4(),
            generation_id=generation_id,
            campaign_type=body.campaign_type,
            variant_index=i,
            status="pending_approval",
            subject_line=v["subject_line"],
            preview_text=v.get("preview_text", ""),
            headline=v["headline"],
            highlight_phrase=v["highlight_phrase"],
            body_intro=v["body_intro"],
            block_1_emoji=v["block_1_emoji"],
            block_1_title=v["block_1_title"],
            block_1_text=v["block_1_text"],
            block_2_emoji=v["block_2_emoji"],
            block_2_title=v["block_2_title"],
            block_2_text=v["block_2_text"],
            closing_message=v["closing_message"],
            ai_prompt=body.prompt,
            approval_token=uuid.uuid4(),
        )
        db.add(variant)
        saved.append(variant)

    db.commit()
    for v in saved:
        db.refresh(v)

    try:
        _send_approval_notification(saved)
    except Exception as e:
        print(f"WARN: could not send approval notification: {e}")

    base = BASE_URL.rstrip("/")
    return {
        "generation_id": str(generation_id),
        "variants": [
            {
                "id": str(v.id),
                "variant_index": v.variant_index,
                "subject_line": v.subject_line,
                "preview_url": f"{base}/variants/{v.approval_token}/preview",
                "status": v.status,
            }
            for v in saved
        ],
        "notification_sent_to": APPROVAL_NOTIFY_EMAIL,
    }


@router.get("/variants/{token}/preview", response_class=HTMLResponse)
def preview_variant(token: str, db: Session = Depends(get_db)):
    """Render the email preview page with approve/reject buttons."""
    variant = db.query(EmailVariant).filter(
        EmailVariant.approval_token == token
    ).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    email_html = _render_variant_email_html(variant)

    siblings = db.query(EmailVariant).filter(
        EmailVariant.generation_id == variant.generation_id
    ).count()

    page_template = jinja_env.get_template("variant_preview.html")
    html = page_template.render(
        variant_index=variant.variant_index,
        total_variants=siblings,
        status=variant.status,
        subject_line=variant.subject_line,
        preview_text=variant.preview_text or "",
        campaign_type=variant.campaign_type,
        approval_token=str(variant.approval_token),
        reviewer_notes=variant.reviewer_notes or "",
        created_at=variant.created_at.strftime("%d/%m/%Y %H:%M") if variant.created_at else "",
        email_html=email_html,
    )
    return HTMLResponse(content=html)


@router.post("/variants/{token}/approve", response_class=HTMLResponse)
def approve_variant(token: str, db: Session = Depends(get_db)):
    """Mark a variant as approved."""
    variant = db.query(EmailVariant).filter(
        EmailVariant.approval_token == token
    ).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    if variant.status != "pending_approval":
        raise HTTPException(status_code=409, detail=f"Variant is already '{variant.status}'")

    variant.status = "approved"
    variant.approved_at = datetime.now(timezone.utc)
    db.commit()

    base = BASE_URL.rstrip("/")
    return HTMLResponse(content=f"""
    <!doctype html><html lang="es"><head>
      <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
      <title>Aprobada — Pika Pika</title>
      <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;900&display=swap" rel="stylesheet">
      <style>body{{font-family:'Nunito',Arial,sans-serif;background:#F7FFF5;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
      .card{{background:#fff;border-radius:20px;padding:48px 40px;text-align:center;max-width:420px;box-shadow:0 4px 24px rgba(0,0,0,.08)}}
      .icon{{font-size:52px;margin-bottom:16px}} h1{{font-size:22px;font-weight:900;color:#5B8C5A;margin-bottom:8px}}
      p{{color:#6b7280;font-size:15px;line-height:1.6;margin-bottom:24px}}
      a{{color:#FF7A3D;font-weight:700;text-decoration:none}}</style>
    </head><body>
      <div class="card">
        <div class="icon">✅</div>
        <h1>¡Variante {variant.variant_index} aprobada!</h1>
        <p>Asunto: <strong>"{variant.subject_line}"</strong><br><br>
        Un administrador confirmará el envío a los clientes desde el panel.</p>
        <a href="{base}/variants/{token}/preview">Ver variante</a>
      </div>
    </body></html>
    """)


@router.post("/variants/{token}/reject", response_class=HTMLResponse)
def reject_variant(token: str, notes: str = Form(default=""), db: Session = Depends(get_db)):
    """Mark a variant as rejected."""
    variant = db.query(EmailVariant).filter(
        EmailVariant.approval_token == token
    ).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    if variant.status != "pending_approval":
        raise HTTPException(status_code=409, detail=f"Variant is already '{variant.status}'")

    variant.status = "rejected"
    variant.rejected_at = datetime.now(timezone.utc)
    variant.reviewer_notes = notes.strip() or None
    db.commit()

    base = BASE_URL.rstrip("/")
    notes_line = f'<p><em>"{notes.strip()}"</em></p>' if notes.strip() else ""
    return HTMLResponse(content=f"""
    <!doctype html><html lang="es"><head>
      <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
      <title>Rechazada — Pika Pika</title>
      <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;900&display=swap" rel="stylesheet">
      <style>body{{font-family:'Nunito',Arial,sans-serif;background:#F7FFF5;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
      .card{{background:#fff;border-radius:20px;padding:48px 40px;text-align:center;max-width:420px;box-shadow:0 4px 24px rgba(0,0,0,.08)}}
      .icon{{font-size:52px;margin-bottom:16px}} h1{{font-size:22px;font-weight:900;color:#111;margin-bottom:8px}}
      p{{color:#6b7280;font-size:15px;line-height:1.6;margin-bottom:8px}}
      a{{color:#FF7A3D;font-weight:700;text-decoration:none}}</style>
    </head><body>
      <div class="card">
        <div class="icon">❌</div>
        <h1>Variante {variant.variant_index} rechazada</h1>
        {notes_line}
        <p>Podés generar nuevas variantes desde el panel de administración.</p>
        <a href="{base}/variants/{token}/preview">Ver variante</a>
      </div>
    </body></html>
    """)


@router.post("/admin/variants/{variant_id}/send", dependencies=[Depends(require_admin_key)])
def confirm_send_variant(variant_id: str, db: Session = Depends(get_db)):
    """Final admin confirmation: queue the approved variant to all eligible customers."""
    variant = db.query(EmailVariant).filter(EmailVariant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    if variant.status != "approved":
        raise HTTPException(status_code=409, detail=f"Variant status is '{variant.status}', must be 'approved'")

    result = db.execute(text("""
        INSERT INTO message_outbox (
            id, customer_id, to_identity_id, template_key, channel, payload, status, scheduled_for, created_at
        )
        SELECT
            gen_random_uuid(),
            ci.customer_id,
            ci.id,
            'ai_variant_v1',
            'email',
            jsonb_build_object(
                'variant_id',       :variant_id::text,
                'subject_line',     :subject_line,
                'headline',         :headline,
                'highlight_phrase', :highlight_phrase,
                'body_intro',       :body_intro,
                'block_1_emoji',    :block_1_emoji,
                'block_1_title',    :block_1_title,
                'block_1_text',     :block_1_text,
                'block_2_emoji',    :block_2_emoji,
                'block_2_title',    :block_2_title,
                'block_2_text',     :block_2_text,
                'closing_message',  :closing_message
            ),
            'queued',
            now(),
            now()
        FROM customer_identities ci
        JOIN (
            SELECT DISTINCT ON (c2.customer_id) c2.customer_id, c2.status
            FROM consents c2
            WHERE c2.channel = 'email'
              AND c2.purpose = 'promotions'
            ORDER BY c2.customer_id, c2.created_at DESC
        ) latest_consent ON latest_consent.customer_id = ci.customer_id
        WHERE ci.channel = 'email'
          AND latest_consent.status = 'granted'
          AND NOT EXISTS (
              SELECT 1 FROM message_outbox mo2
              WHERE mo2.to_identity_id = ci.id
                AND mo2.status IN ('queued', 'sent')
                AND (mo2.payload->>'variant_id') = :variant_id::text
          )
    """), {
        "variant_id":       str(variant.id),
        "subject_line":     variant.subject_line,
        "headline":         variant.headline,
        "highlight_phrase": variant.highlight_phrase,
        "body_intro":       variant.body_intro,
        "block_1_emoji":    variant.block_1_emoji,
        "block_1_title":    variant.block_1_title,
        "block_1_text":     variant.block_1_text,
        "block_2_emoji":    variant.block_2_emoji,
        "block_2_title":    variant.block_2_title,
        "block_2_text":     variant.block_2_text,
        "closing_message":  variant.closing_message,
    })

    queued_count = result.rowcount
    variant.status = "sent"
    db.commit()

    return {
        "variant_id":    str(variant.id),
        "subject_line":  variant.subject_line,
        "queued_count":  queued_count,
        "status":        "sent",
    }
