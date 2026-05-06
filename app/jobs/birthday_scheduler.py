import json
from sqlalchemy import text
from sqlalchemy.orm import Session


def _get_campaign_config(db: Session) -> dict:
    row = db.execute(
        text("SELECT promo_code, promo_text, image_url FROM birthday_campaign_config WHERE id = 1")
    ).mappings().first()
    if not row:
        return {}
    return {k: v for k, v in dict(row).items() if v is not None}


def queue_birthday_emails(db: Session) -> dict:
    config = _get_campaign_config(db)
    total = 0

    for days_ahead in (7, 3):
        result = db.execute(
            text("""
                with email_identity as (
                    select distinct on (ci.customer_id)
                        ci.customer_id,
                        ci.id as identity_id,
                        ci.value as email
                    from customer_identities ci
                    where ci.channel = 'email'::channel_type
                    order by ci.customer_id, ci.is_primary desc, ci.id asc
                ),
                latest_consent as (
                    select distinct on (customer_id, channel, purpose)
                        customer_id, status
                    from consents
                    where purpose = 'promotions'
                      and channel = 'email'::channel_type
                    order by customer_id, channel, purpose, created_at desc
                ),
                eligible as (
                    select
                        c.id as customer_id,
                        c.first_name as name,
                        ei.identity_id,
                        ei.email
                    from customers c
                    join email_identity ei on ei.customer_id = c.id
                    join latest_consent lc on lc.customer_id = c.id and lc.status = 'granted'
                    where c.birth_month is not null
                      and c.birth_day   is not null
                      and c.birth_month = extract(month from current_date + (:days_ahead || ' days')::interval)
                      and c.birth_day   = extract(day   from current_date + (:days_ahead || ' days')::interval)
                      and not exists (
                            select 1 from message_outbox mo
                            where mo.customer_id  = c.id
                              and mo.template_key = 'birthday_v1'
                              and extract(year from mo.created_at) = extract(year from current_date)
                              and mo.status != 'failed'
                      )
                )
                insert into message_outbox
                    (customer_id, to_identity_id, channel, template_key, payload, scheduled_for, status)
                select
                    e.customer_id,
                    e.identity_id,
                    'email'::channel_type,
                    'birthday_v1',
                    :payload::jsonb || jsonb_build_object('name', e.name, 'email', e.email),
                    now(),
                    'queued'::outbox_status
                from eligible e
                on conflict do nothing
                returning id
            """),
            {"days_ahead": days_ahead, "payload": json.dumps(config)},
        )
        inserted = result.fetchall()
        total += len(inserted)
        if inserted:
            print(f"Birthday scheduler: queued {len(inserted)} email(s) for birthdays in {days_ahead} days")

    db.commit()
    return {"inserted": total}
