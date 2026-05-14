# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the application

```bash
# FastAPI web server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Background email delivery worker (separate process)
python worker.py
```

Set `EMAIL_SEND_MODE=TEST` and `TEST_TO_EMAIL=your@email.com` in `.env` to redirect all outgoing emails to a single address during local testing.

## Key environment variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL (psycopg3) connection string |
| `APP_BASE_URL` | Absolute base URL — used to build logo URLs in email templates |
| `ADMIN_API_KEY` / `BUILDER_API_KEY` | API key auth on all `/admin/*` routes |
| `SMTP_*` | Gmail SMTP credentials |
| `OPENAI_API_KEY` | GPT-4o-mini for email variant generation |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | Image uploads to Supabase Storage |
| `EMAIL_SEND_MODE` / `TEST_TO_EMAIL` | Set to `TEST` to redirect all sends |

## Architecture

### Processes

**`app/main.py`** — FastAPI app. Registers all routers, rate-limiting (slowapi, 10 req/min on `/signup`), and static file serving.

**`worker.py`** — Blocking polling loop. Every few seconds it queries `message_outbox` for `scheduled_for <= now()` rows with status `queued`, renders the template, sends via SMTP, and marks `sent` or `failed`. After sending a birthday email it calls `reschedule_birthday()` to queue next year's sends.

### Database-driven job queue

All scheduled sends live in `message_outbox`. There is no external job system. Birthday emails are inserted at signup time with future `scheduled_for` values (18:30 UTC = 15:30 ART, 7 and 3 days before the birthday). Weekly promo emails are inserted by the admin email builder with `scheduled_for` set to the next Thursday at 20:00 UTC (17:00 ART).

Key constraint: `UNIQUE (customer_id, channel, template_key, scheduled_for)`. When re-queuing a promo, the router DELETEs the existing queued row before INSERTing the new one.

### Routers

| Router | Prefix | Purpose |
|---|---|---|
| `signup.py` | `/signup` | New customer registration; queues `welcome_v1` email |
| `admin_variants.py` | `/admin` | AI variant generation (GPT-4o-mini), preview, approval flow, promo queueing |
| `admin_ui.py` | `/admin` | Dashboard and customer list HTML pages |
| `admin_api.py` | `/admin` | JSON API powering the dashboard (summary, outbox, debug) |
| `admin_dashboard.py` | `/admin` | Customers list + campaign metrics API |
| `birthday_builder.py` | `/admin/birthday-builder` | Birthday campaign config UI |
| `story_builder.py` | `/admin/story-builder` | Instagram story image builder |
| `unsubscribe.py` | `/unsubscribe` | Consent revocation via signed tokens |
| `meta_webhook.py` | `/webhook/meta` | Instagram DM webhook → customer attributes |

### Services

**`app/services/signup_service.py`** — `create_signup()` handles upsert-safe registration, consent grants, and calls `_schedule_birthday_emails()` if birth date is provided.

**`app/services/ai_copy_service.py`** — `generate_variants()` calls GPT-4o-mini and returns two structured email copy options.

### Email templates

Jinja2 HTML templates in `app/templates/`. The four campaign templates are:

- `welcome_email.html` — sent once on signup (`welcome_v1`)
- `birthday_email.html` — birthday campaign (`birthday_v1`)
- `promo_email.html` — weekly promo (`promo_v1`)
- AI-generated variants rendered inline by `admin_variants.py`

All templates use `logo_cream.png?v=2` with an absolute `APP_BASE_URL` prefix. Gmail strips `display:flex` — email layout uses `text-align:center` + `display:inline-block` on images, never flexbox.

### Authentication

Header `X-Admin-Key` checked against `ADMIN_API_KEY` or `BUILDER_API_KEY`. Both keys are accepted everywhere. Missing or wrong key → 401.

### Timezones

Argentina = UTC-3 (no DST). All `scheduled_for` values are stored as UTC. The convention throughout the codebase is `18:30 UTC = 15:30 ART` for birthday emails and `20:00 UTC = 17:00 ART` for Thursday promos. Use `timezone(timedelta(hours=-3))` for ART; never hardcode the string `America/Argentina/Buenos_Aires` in Python — psycopg3 has no issue with it but stick to the offset pattern used elsewhere.

### psycopg3 gotcha

psycopg3 parses `:param::cast` as a malformed parameter. Always use `CAST(:param AS type)` instead of the `::` shorthand in raw SQL strings passed to SQLAlchemy `text()`.
