from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
WEEKLY_SEND_HOUR_UTC = 13  # Monday 13:00 UTC

def next_monday_utc_at(hour_utc: int) -> datetime:
    now = datetime.now(timezone.utc)
    # Monday = 0 ... Sunday = 6
    days_ahead = (0 - now.weekday()) % 7
    candidate = (now + timedelta(days=days_ahead)).replace(
        hour=hour_utc, minute=0, second=0, microsecond=0
    )
    # If it's already past Monday@hour this week, schedule next week
    if candidate <= now:
        candidate += timedelta(days=7)
    return candidate


def queue_weekly_promo(db, template_key="weekly_promo_v1", scheduled_for=None):
    if scheduled_for is None:
        scheduled_for = datetime.now(timezone.utc)

    campaign_id = "00000000-0000-0000-0000-000000000000"  # keep yours if you have one
    db_info = db.execute(text("""
    select
    current_database() as db,
    current_schema() as schema,
    current_user as user,
    inet_server_addr() as server_ip,
    inet_server_port() as server_port
    """)).mappings().first()
    print("DB INFO (queue-weekly):", dict(db_info))
    result = db.execute(
    text("""
        with latest_consent as (
          select distinct on (customer_id, channel, purpose)
            customer_id, channel, purpose, status
          from consents
          where purpose = 'promotions'
            and channel = 'email'::channel_type
          order by customer_id, channel, purpose, created_at desc
        ),
        email_identity as (
          -- pick one email identity per customer (prefer primary)
          select distinct on (ci.customer_id)
            ci.customer_id,
            ci.id as identity_id,
            ci.value as email
          from customer_identities ci
          where ci.channel = 'email'::channel_type
          order by ci.customer_id, ci.is_primary desc, ci.id asc
        ),
        interests as (
          -- interests stored as customer_attributes(key='interests', value jsonb array)
          select
            c.id as customer_id,
            coalesce(ca.value, '[]'::jsonb) as interests
          from customers c
          left join customer_attributes ca
            on ca.customer_id = c.id
           and ca.key = 'interests'
        ),
        eligible as (
          select
            c.id as customer_id,
            ei.identity_id,
            ei.email,
            c.first_name as name,
            it.interests
          from customers c
          join email_identity ei on ei.customer_id = c.id
          join latest_consent lc on lc.customer_id = c.id and lc.status = 'granted'
          join interests it on it.customer_id = c.id
        )
        insert into message_outbox (
          campaign_id, customer_id, channel, to_identity_id,
          template_key, payload, scheduled_for, status
        )
        select
          :campaign_id,
          e.customer_id,
          'email'::channel_type,
          e.identity_id,
          :template_key,
          jsonb_build_object(
            'name', e.name,
            'email', e.email,
            'interests', e.interests
          ),
          :scheduled_for,
          'queued'::outbox_status
        from eligible e
        on conflict (customer_id, channel, template_key, scheduled_for) do nothing
        returning id
    """),
    {
        "campaign_id": campaign_id,
        "template_key": template_key,
        "scheduled_for": scheduled_for,
    },
)
    count_now = db.execute(text("select count(*) from public.message_outbox")).scalar_one()
    print("OUTBOX COUNT (before commit):", count_now)

    db.commit()

    count_after = db.execute(text("select count(*) from public.message_outbox")).scalar_one()
    print("OUTBOX COUNT (after commit):", count_after)
    inserted = result.fetchall()
    return {"inserted": len(inserted)}