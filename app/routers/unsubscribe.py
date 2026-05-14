from fastapi import APIRouter, Query, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()


def _page(title: str, emoji: str, heading: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title} — Principessa Pastelería</title>
  <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;900&display=swap" rel="stylesheet">
  <style>
    body{{font-family:'Nunito',Arial,sans-serif;background:#FBF4EE;display:flex;align-items:center;
          justify-content:center;min-height:100vh;margin:0;}}
    .card{{background:#fff;border-radius:20px;padding:48px 40px;text-align:center;
           max-width:420px;width:90%;box-shadow:0 4px 24px rgba(0,0,0,.08);}}
    .emoji{{font-size:52px;margin-bottom:16px;}}
    h1{{font-size:22px;font-weight:900;color:#6B3217;margin:0 0 12px;}}
    p{{color:#6b7280;font-size:15px;line-height:1.6;margin:0;}}
  </style>
</head>
<body>
  <div class="card">
    <div class="emoji">{emoji}</div>
    <h1>{heading}</h1>
    <p>{body}</p>
  </div>
</body>
</html>"""


@router.get("/unsubscribe", response_class=HTMLResponse)
def unsubscribe(
    channel: str = Query(...),
    value: str = Query(...),
    db: Session = Depends(get_db)
):
    result = db.execute(
        text("""
            select c.id
            from customers c
            join customer_identities ci on ci.customer_id = c.id
            where ci.channel = CAST(:channel AS channel_type)
            and ci.value = :value
        """),
        {"channel": channel, "value": value}
    ).fetchone()

    if not result:
        return HTMLResponse(
            _page(
                "No encontrado",
                "🤔",
                "No encontramos tu contacto",
                "Es posible que ya hayas cancelado tu suscripción o que el link haya expirado.",
            ),
            status_code=404,
        )

    customer_id = result[0]

    db.execute(
        text("""
            insert into consents (customer_id, channel, purpose, status, revoked_at, proof)
            values (:customer_id,
                    CAST(:channel AS channel_type),
                    'promotions'::consent_purpose,
                    'revoked'::consent_status,
                    now(),
                    '{}'::jsonb)
        """),
        {"customer_id": customer_id, "channel": channel}
    )

    db.commit()

    return HTMLResponse(
        _page(
            "Baja confirmada",
            "✅",
            "Te diste de baja correctamente",
            "Ya no recibirás más emails promocionales de Principessa Pastelería.",
        )
    )
