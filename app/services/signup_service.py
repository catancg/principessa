import json
from datetime import date, timedelta, datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.schemas.signup import SignupIn
ALLOWED_INTERESTS = {"torta_ricota", "cheesecake", "torta_matilda", "carrot_cake", "ricota_dulce_leche", "torta_balcarce"}


def create_signup(db: Session, data) -> tuple[str, str, bool]:
    """
    Creates/ensures:
      - customer row
      - email identity row (channel=email)
      - consent granted for promotions (no repeated 'granted' spam)
    """
    name = data.name.strip()
    email = data.email.strip().lower()

    # 0) start tx
    # (If you're already wrapping commit/rollback outside, keep consistent.)
    # Here we assume router/service commits elsewhere OR you commit here.
    # We'll not commit here to match your style: db.commit() outside.
    # If you want it self-contained, add db.commit() at the end.

    # 1) Find existing email identity (prevents duplicate customers)
    row = db.execute(
        text("""
            select ci.id as identity_id, ci.customer_id
            from customer_identities ci
            where ci.channel = 'email'::channel_type
              and ci.value = :email
            limit 1
        """),
        {"email": email},
    ).first()

    if row:
        is_new_customer = False
        customer_id = row.customer_id
        identity_id = row.identity_id

        db.execute(
            text("""
                update customers
                set first_name = :name, updated_at = now()
                where id = :customer_id
            """),
            {"name": name, "customer_id": customer_id},
        )
    else:
        is_new_customer = True
        # 2) Create customer
        customer_id = db.execute(
            text("""
                insert into customers (first_name)
                values (:name)
                returning id
            """),
            {"name": name},
        ).scalar_one()

        # 3) Create email identity
        identity_id = db.execute(
            text("""
                insert into customer_identities (customer_id, channel, value, is_primary)
                values (:customer_id, 'email'::channel_type, :email, true)
                on conflict (channel, value) do nothing
                returning id
            """),
            {"customer_id": customer_id, "email": email},
        ).scalar_one_or_none()

        # Race safety: if conflict happened, fetch the identity
        if identity_id is None:
            row2 = db.execute(
                text("""
                    select ci.id as identity_id, ci.customer_id
                    from customer_identities ci
                    where ci.channel = 'email'::channel_type
                      and ci.value = :email
                    limit 1
                """),
                {"email": email},
            ).first()
            if not row2:
                raise RuntimeError("Identity insert race: could not fetch existing email identity")
            identity_id = row2.identity_id
            customer_id = row2.customer_id

    # 3b) Save birthday if both fields provided
    birth_month = getattr(data, "birth_month", None)
    birth_day = getattr(data, "birth_day", None)
    if birth_month and birth_day:
        db.execute(
            text("""
                update customers
                set birth_month = :bm, birth_day = :bd, updated_at = now()
                where id = :cid
            """),
            {"bm": birth_month, "bd": birth_day, "cid": customer_id},
        )
        _schedule_birthday_emails(db, customer_id, identity_id, name, birth_month, birth_day)

    # 4) Consent: insert granted only if NOT currently granted
    if getattr(data, "consent_promotions", True):
        db.execute(
            text("""
                insert into consents (customer_id, channel, purpose, status)
                select :customer_id, 'email'::channel_type, 'promotions', 'granted'
                where coalesce(
                    (select status::text from consents
                     where customer_id = :customer_id
                       and channel = 'email'::channel_type
                       and purpose = 'promotions'
                     order by created_at desc
                     limit 1),
                    'none'
                ) != 'granted'
            """),
            {"customer_id": customer_id},
        )

    if is_new_customer:
        db.execute(
            text("""
                insert into message_outbox
                    (customer_id, to_identity_id, channel, template_key, scheduled_for, payload, status)
                values
                    (:customer_id, :identity_id, 'email'::channel_type, 'welcome_v1', now(),
                     CAST(:payload AS jsonb), 'queued')
                on conflict do nothing
            """),
            {
                "customer_id": customer_id,
                "identity_id": identity_id,
                "payload": json.dumps({"name": name}),
            },
        )

    return customer_id, identity_id, is_new_customer


def _schedule_birthday_emails(db, customer_id: int, identity_id: int, name: str, birth_month: int, birth_day: int):
    today = date.today()

    try:
        candidate = date(today.year, birth_month, birth_day)
    except ValueError:
        candidate = date(today.year, birth_month, 28)

    next_bday = candidate if candidate >= today else _next_year_birthday(today.year + 1, birth_month, birth_day)

    for days_before in (7, 3):
        send_date = next_bday - timedelta(days=days_before)
        if send_date < today:
            continue
        scheduled_for = datetime(send_date.year, send_date.month, send_date.day, 18, 30, tzinfo=timezone.utc)
        db.execute(
            text("""
                INSERT INTO message_outbox
                    (customer_id, to_identity_id, channel, template_key, scheduled_for, payload, status)
                SELECT :cid, :iid, 'email'::channel_type, 'birthday_v1',
                       :scheduled_for, CAST(:payload AS jsonb), 'queued'
                WHERE NOT EXISTS (
                    SELECT 1 FROM message_outbox
                    WHERE customer_id  = :cid
                      AND template_key = 'birthday_v1'
                      AND date_trunc('day', scheduled_for AT TIME ZONE 'UTC') = CAST(:sched_day AS date)
                      AND status != 'failed'
                )
            """),
            {
                "cid": customer_id,
                "iid": identity_id,
                "scheduled_for": scheduled_for,
                "payload": json.dumps({"name": name}),
                "sched_day": str(send_date),
            },
        )


def _next_year_birthday(year: int, birth_month: int, birth_day: int) -> date:
    try:
        return date(year, birth_month, birth_day)
    except ValueError:
        return date(year, birth_month, 28)