import json

from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone

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