import os
import time
import smtplib
from pathlib import Path
from email.message import EmailMessage
from datetime import datetime, timezone
import mimetypes
import smtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from sqlalchemy import text
from app.db.session import SessionLocal

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Tienda")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")
BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")
EMAIL_SEND_MODE = os.getenv("EMAIL_SEND_MODE", "LIVE").upper()
TEST_TO_EMAIL = os.getenv("TEST_TO_EMAIL", "").strip()
DRY_RUN_SEEN = set()
DRY_RUN_SLEEP_SECONDS = int(os.getenv("DRY_RUN_SLEEP_SECONDS", "10"))


BASE_DIR = Path(__file__).resolve().parent  # ajustá si tu worker está en otra carpeta
TEMPLATES_DIR = BASE_DIR / "app/templates"
ASSETS_DIR = BASE_DIR / "app/assets"

jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)
def render_email(template_key: str, payload: dict) -> tuple[str, str, str, str | None]:
    """
    Returns: subject, text_body, html_body, logo_path
    """
    if template_key == "weekly_promo_v1":
        subject = "Beneficios exclusivos para vos en Pika Pika 🎁"

        name = (payload.get("name") or "").strip()
        email = (payload.get("email") or "").strip()

        # Texto plano fallback (importante para entregabilidad)
        hi = f"¡Hola {name}! 👋\n\n" if name else "¡Hola! 👋\n\n"
        text_body = (
            hi
            + "Queremos invitarte a nuestro local. Presentando este email tenés un descuento especial.\n\n"
            + "Ubicación: https://maps.google.com/?q=TU_DIRECCION\n"
            + "WhatsApp: https://wa.me/TU_NUMERO\n"
            + "Instagram: https://instagram.com/TU_CUENTA\n\n"
            + "Darte de baja:\n"
            + f"{BASE_URL}/unsubscribe?channel=email&value={email}\n"
        )

        # HTML
        template = jinja_env.get_template("pika_pika_weekly.html")
        html_body = template.render(
            terms_line="Válido por 7 días desde la recepción. No acumulable con otras promos.",
            maps_url="https://maps.google.com/?q=TU_DIRECCION",
            whatsapp_url="https://wa.me/TU_NUMERO",
            address="TU DIRECCIÓN",
            hours="Lun a Sáb 10:00 a 19:00",
            instagram_url="https://instagram.com/TU_CUENTA",
            instagram_handle="@TU_CUENTA",
            unsubscribe_url=f"{BASE_URL}/unsubscribe?channel=email&value={email}",
        )

        logo_path = str(ASSETS_DIR / "logo.png")  # poné tu logo acá
        return subject, text_body, html_body, logo_path

    # fallback
    return "Novedades", "Hola!", "<p>Hola!</p>", None
#def render_email(template_key: str, payload: dict) -> tuple[str, str]:
    if template_key == "weekly_promo_v1":
        subject = "Beneficios exclusivos para vos en Pika Pika 🎁"

        name = (payload.get("name") or "").strip()
        email = (payload.get("email") or "").strip()
        interests = payload.get("interests") or []

        # Nice, optional interest line
        interest_map = {
            "baby_items": "artículos para bebé",
            "toys": "juguetes",
            "cochesitos": "cochesitos",
            "cunas": "cunas",
        }
        picked = [interest_map.get(i, i) for i in interests]
        interest_line = ""
        if picked:
            interest_line = "🧸 En base a tus intereses (" + ", ".join(picked) + "), te preparamos recomendaciones y promos.\n\n"

        hi = f"¡Hola {name}! 👋\n\n" if name else "¡Hola! 👋\n\n"

        body = (
            hi
            + "Esta semana tenemos beneficios especiales pensados para vos y tu bebé 💕\n\n"
            + interest_line
            + "🎁 Presentando este email en el local accedés a descuentos exclusivos\n"
            + "y recomendaciones personalizadas.\n\n"
            + "¡Te esperamos en la tienda!\n\n"
            + "— — — — — — — — — — — — — — — — —\n"
            + "Si preferís no recibir más mensajes, podés darte de baja acá:\n"
            + f"https://baby-engagement-api.onrender.com/unsubscribe?channel=email&value={email}\n"
        )
        return subject, body

    return "Novedades", "Hola!"
#def send_smtp(to_email: str, subject: str, body: str):

    msg = EmailMessage()
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)


def send_smtp(to_email: str, subject: str, text_body: str, html_body: str | None = None, logo_path: str | None = None):
    msg = EmailMessage()
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    # Texto plano siempre
    msg.set_content(text_body)

    # HTML opcional
    if html_body:
        msg.add_alternative(html_body, subtype="html")

        # Logo inline por CID (si hay HTML)
        if logo_path:
            p = Path(logo_path)
            if p.exists():
                ctype, _ = mimetypes.guess_type(str(p))
                maintype, subtype = (ctype.split("/", 1) if ctype else ("image", "png"))

                with open(p, "rb") as f:
                    data = f.read()

                # El HTML tiene <img src="cid:logo">
                html_part = msg.get_payload()[-1]
                html_part.add_related(
                    data,
                    maintype=maintype,
                    subtype=subtype,
                    cid="<logo>",
                    filename=p.name,
                )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
def fetch_next_batch(db, batch_size: int = 25):
    # Lock rows so multiple workers can run safely.
    rows = db.execute(text("""
        select mo.id, mo.template_key, ci.value as to_email
        from message_outbox mo
        join customer_identities ci on ci.id = mo.to_identity_id
        where mo.status = 'queued'
          and mo.channel = 'email'
          and mo.scheduled_for <= now()
        order by mo.created_at
        for update skip locked
        limit :limit
    """), {"limit": batch_size}).fetchall()
    return rows

def mark_sent(db, outbox_id):
    db.execute(text("""
        update message_outbox
        set status = 'sent',
            sent_at = now()
        where id = :id
    """), {"id": outbox_id})

def mark_failed(db, outbox_id, reason: str):
    db.execute(text("""
        update message_outbox
        set status = 'failed'
        where id = :id
    """), {"id": outbox_id})
    # Optional: add message_delivery table later for detailed errors/logs.

def main():
    missing = [k for k in ["SMTP_HOST","SMTP_USERNAME","SMTP_PASSWORD","SMTP_FROM_EMAIL"] if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing SMTP env vars: {missing}")
    print(BASE_DIR,TEMPLATES_DIR,ASSETS_DIR)
    print("Worker started. Polling outbox...")

    while True:
        db = SessionLocal()
        try:
            db.begin()
            batch = fetch_next_batch(db, batch_size=25)

            if not batch:
                db.commit()
                time.sleep(3)
                continue

            for outbox_id, template_key, to_email in batch:
                original_to = to_email  # keep for logs even if we overwrite to_email
                try:
                    subject, text_body, html_body, logo_path = render_email(template_key, {"email": original_to})

                    # ---- SAFE MODES ----
                    if EMAIL_SEND_MODE == "DRY_RUN":
                        print("DRY_RUN -> Would send", outbox_id, "to:", original_to, "template:", template_key)
                        DRY_RUN_SEEN.add(outbox_id)
                        # Do NOT mark sent. Leave it queued.
                        continue

                    if EMAIL_SEND_MODE == "TEST":
                        if not TEST_TO_EMAIL:
                            raise RuntimeError("EMAIL_SEND_MODE=TEST but TEST_TO_EMAIL is not set")

                        to_email = TEST_TO_EMAIL
                        subject = f"[TEST] {subject}"

                        text_body = (
                            "⚠️ MODO PRUEBA\n"
                            f"Este email originalmente iba dirigido a: {original_to}\n\n"
                            + text_body
                        )

                        if html_body:
                            html_body = (
                                "<div style='padding:12px;background:#fff3cd;border:1px solid #ffeeba;"
                                "border-radius:8px;font-family:Arial,Helvetica,sans-serif;font-size:12px;'>"
                                f"⚠️ MODO PRUEBA<br>Original: {original_to}"
                                "</div>"
                                + html_body
                            )

                    # ---- LIVE / TEST SEND ----
                    send_smtp(to_email, subject, text_body, html_body=html_body, logo_path=logo_path)
                    mark_sent(db, outbox_id)

                    print("SENT", outbox_id, "->", to_email, "(original:", original_to, ")")

                except Exception as e:
                    mark_failed(db, outbox_id, repr(e))
                    print("FAILED", outbox_id, "->", original_to, "error:", repr(e))

            db.commit()
            if EMAIL_SEND_MODE == "DRY_RUN":
                time.sleep(DRY_RUN_SLEEP_SECONDS)

        except Exception as e:
            db.rollback()
            print("WORKER LOOP ERROR:", repr(e))
        finally:
            db.close()

if __name__ == "__main__":
    main()
