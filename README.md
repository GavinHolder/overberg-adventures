# Overstrand Adventures — PWA

**Client:** Overstrand Adventures — guided adventure tours, Overberg/Kogelberg region, South Africa
**Stack:** Django 6 · HTMX · Alpine.js · Bootstrap 5 · PostgreSQL
**Started:** 2026-02-27
**Status:** Phase 5 of 15 complete — 46 tests passing

---

## What's Built

### Infrastructure (Phase 1)
Three separate Docker infrastructure stacks + app stack, all managed via Portainer:

| Stack | Purpose | Location |
|-------|---------|---------|
| `traefik` | Reverse proxy + routing | `deploy/traefik/` |
| `portainer` | Docker management UI | `deploy/portainer/` |
| `redis` | Celery broker + cache | `deploy/redis/` |
| `app` | Django app (web + db + celery + beat) | `deploy/app/` |

Dashboard ports locked to localhost (SSH tunnel required). Portainer pinned to `2.21.4`. Redis with AOF persistence. App container uses non-root user; `entrypoint.sh` runs migrations before gunicorn starts.

SSH setup guide: `deploy/SSH_SETUP.md`

### Django Project (Phase 2)
- Django 6.0.2, Python 3.12
- All env vars via `python-decouple` (no hardcoded values)
- `DEV_MODE` — double-guarded: `config('DEV_MODE', ...) and DEBUG` (can never activate in production)
- `TIME_ZONE = 'Africa/Johannesburg'`
- WhiteNoise for static files; SendGrid (django-anymail) for email; Celery + Redis for async tasks
- 10 app skeletons: `accounts`, `tours`, `bookings`, `payments`, `notifications`, `maps`, `nfc`, `landing`, `sos`, `backups`
- `pytest-django` configured

### Authentication (Phase 3)
Complete auth system matching the prototype UI:

- **Email signup** — OTP code emailed (6-digit, 15-minute expiry, 3-attempt lockout)
- **Social login** — Google + Facebook OAuth via django-allauth (scaffold ready; client provides app credentials)
- **DEV_MODE bypass** — simple username/password login; OTP shown in UI and auto-filled
- **5-step profile setup wizard** — HTMX partial swaps, no full page reload:
  1. Personal Details (name, WhatsApp, DOB)
  2. Health Info (fitness 1–5, medical, dietary)
  3. Permissions (location + notifications)
  4. Personal Notes (visible to guide)
  5. Indemnity Agreement (scroll + Alpine.js modal confirm)
- **UserProfile model** — roles (GUEST/GUIDE/OPERATOR/ADMIN), wizard completion tracking, `setup_complete` property
- **Design system** — cream background `#FAF5EE`, orange primary `#F97316`, teal secondary `#0D9488`, card `border-radius: 16px`

### Tours System (Phase 4)
- **ActivityCategory** — name, icon, colour, ordering; 10 initial categories seeded (Hiking, Food & Dining, Kayaking, Cycling, Scenic Drive, Whale Watching, Swimming, Photography, Cultural, Accommodation)
- **Tour** — name, unique tour code, guide FK, datetime, location (name/lat/lng), capacity, status (DRAFT/ACTIVE/COMPLETED/CANCELLED), GeoJSON polygon, fitness/age restrictions, RSVP deadline; `spots_remaining` + `is_full` properties
- **ItineraryItem** — day + ordered activities per tour, category, timing, difficulty (EASY/MODERATE/HARD), distance
- **MapRouteWaypoint** — ordered lat/lng waypoints for walking/driving route overlay
- **TourCodeWord** — pool of 54 Overberg/nature-themed single words (fynbos, pelican, milkwood, protea, etc.); `generate()` uses `select_for_update()` inside `transaction.atomic()` — concurrency-safe

### Bookings + Payments (Phase 5)
- **Booking model** — RSVP_PENDING → CONFIRMED flow; `unique_together` prevents duplicate bookings; `tour_code` assigned after payment confirmation
- **BookingManager.create_from_rsvp** — atomic capacity check with `select_for_update()` on tour row; raises `ValueError` if full
- **Payment adapter pattern** (ABC):
  - `ManualPaymentAdapter` — admin captures payment manually; no webhook
  - `DevSimulateAdapter` — `simulate_payment()` instantly confirms booking in DEV_MODE
  - `PayFastAdapter` / `PeachPaymentsAdapter` — stubs scaffolded for Phase 10
  - `get_payment_adapter()` factory — dispatches on `PAYMENT_GATEWAY` env var + `DEV_MODE`
  - Email dispatch uses `transaction.on_commit()` — task only fires after DB commit is durable

---

## Test Suite

```
46 passed, 0 failed (as of Phase 5)
```

| App | Test file | Coverage |
|-----|-----------|---------|
| accounts | `tests/test_models.py`, `tests/test_views.py` | EmailOTP, UserProfile, OTP verification, wizard |
| tours | `tests/test_models.py` | All 5 models, seed commands, atomic generate |
| bookings | `tests/test_booking.py` | RSVP, capacity, uniqueness, spots_remaining/is_full |
| payments | `tests/test_adapters.py` | Factory dispatch, manual confirm, dev simulate, DEV_MODE guard |

Run all tests:
```bash
pytest -v
```

---

## Project Structure

```
overberg_adventures/          ← Django project
├── apps/
│   ├── accounts/             ← Auth, profiles, social login, email OTP
│   ├── tours/                ← Tour model, itinerary items, tour codes, seed commands
│   ├── bookings/             ← Bookings, RSVPs, capacity management
│   ├── payments/             ← Payment adapter ABC + Manual/Dev/PayFast/Peach adapters
│   ├── notifications/        ← Push notifications, Celery tasks (placeholder)
│   ├── maps/                 ← Polygon storage, route planning (Phase 7)
│   ├── nfc/                  ← NFC check-in, tagging (Phase 12)
│   ├── landing/              ← GrapesJS landing page, maintenance mode (Phase 11)
│   ├── sos/                  ← SOS feature, emergency contacts (Phase 6)
│   └── backups/              ← Backup/restore management (Phase 13)
├── deploy/
│   ├── traefik/              ← Traefik stack
│   ├── portainer/            ← Portainer stack
│   ├── redis/                ← Redis stack
│   ├── app/                  ← App stack (docker-compose.yml)
│   └── SSH_SETUP.md          ← VM setup guide
├── templates/
│   ├── base_app.html         ← PWA base (Bootstrap 5, HTMX, Alpine.js, bottom nav)
│   ├── app/partials/         ← Bottom nav, shared partials
│   └── accounts/             ← Login, OTP verify, 5-step profile wizard
├── static/
│   └── css/app.css           ← Design token system + component classes
├── Dockerfile
├── entrypoint.sh
├── .env.example
├── CHANGELOG.md              ← Detailed change history
└── ROADMAP.md                ← Upcoming phases
```

---

## Design Language

| Token | Value |
|-------|-------|
| Background | `#FAF5EE` (warm cream) |
| Primary | `#F97316 → #EA580C` (orange gradient) |
| Secondary | `#0D9488` (teal — food/dining accent) |
| Surface | `#FFFFFF` |
| Text | `#1C1917` |
| Text muted | `#78716C` |
| Border | `#E7E5E4` |
| Danger | `#EF4444` |
| Card | white, `border-radius: 16px`, subtle shadow |
| Nav | 5-tab bottom bar: Home · Itinerary · SOS · Map · Profile |
| Maps | Google Maps satellite view |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 6.0.2 |
| Frontend templating | Django Templates + HTMX + Alpine.js |
| CSS | Bootstrap 5.3 + custom design tokens |
| Database | PostgreSQL (SQLite for local dev) |
| Auth | django-allauth (Google + Facebook + email/OTP) |
| Email | SendGrid (django-anymail) |
| Maps | Google Maps JavaScript API v3 (Phase 7) |
| Push notifications | Web Push + django-webpush + FCM (Phase 8) |
| Payments | Gateway-agnostic adapter — PayFast/Peach (Phase 10) |
| NFC | Web NFC API, Android Chrome only (Phase 12) |
| Landing page builder | GrapesJS (Phase 11) |
| Background tasks | Celery + Redis |
| Deployment | Docker + Portainer + Traefik |
| File storage | Local (MVP) → S3-compatible post-MVP |

---

## Environment Setup

```bash
# Copy env file and fill in values
cp .env.example .env

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Seed reference data
python manage.py seed_categories
python manage.py seed_tour_codes

# Run tests
pytest -v

# Start dev server
python manage.py runserver
```

Key env vars:

| Variable | Required | Notes |
|----------|----------|-------|
| `DJANGO_SECRET_KEY` | Yes | Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | Yes | `True` for dev, `False` for prod |
| `DEV_MODE` | Optional | Only active when `DEBUG=True` |
| `DATABASE_URL` | Prod only | Defaults to SQLite for local dev |
| `SENDGRID_API_KEY` | Prod | Console email fallback in dev |
| `GOOGLE_CLIENT_ID/SECRET` | Optional | OAuth login |
| `FACEBOOK_APP_ID/SECRET` | Optional | OAuth login |
| `GOOGLE_MAPS_API_KEY` | Phase 7 | |
| `REDIS_URL` | Prod | `redis://localhost:6379/0` default |

---

## Client Requirements Status

| Requirement | Status |
|-------------|--------|
| Email auth + OTP verification | ✅ Built |
| Google + Facebook OAuth | ✅ Scaffolded (needs client credentials) |
| 5-step profile setup wizard | ✅ Built |
| Tour code system (single Overberg word) | ✅ Built |
| Booking + RSVP + capacity enforcement | ✅ Built |
| Payment adapter (gateway-agnostic) | ✅ Scaffolded |
| Google Maps (satellite, markers, polygons, routes) | Phase 7 |
| Push notifications + notification manager | Phase 8 |
| Backend admin panel | Phase 9 |
| PayFast / Peach Payments | Phase 10 |
| Landing page + GrapesJS | Phase 11 |
| NFC check-in | Phase 12 |
| Backup / restore | Phase 13 |
| DEV MODE overlay | Phase 14 |
| PWA manifest + service worker + offline | Phase 15 |
| SOS screen | Phase 6 |
| Full-screen map tab | Phase 6 |

---

## Open Items (Waiting on Client)

| Item | Notes |
|------|-------|
| VM IP + SSH credentials | For deployment |
| Google Maps GCP project | New project from scratch |
| Payment gateway preference | PayFast vs Peach Payments |
| Domain name | IP-based for dev; domain needed for HTTPS |
| SendGrid API key | Transactional email |
| Google OAuth credentials | Client ID + Secret |
| Facebook App credentials | App ID + Secret |

---

## Session Log

| Date | Summary |
|------|---------|
| 2026-02-27 | Initial client brief; all 15 UI screens reviewed; README + design doc created; questions resolved; new requirements captured (tour codes, dev mode, VM infra, payment adapter) |
| 2026-02-27 | Phases 1–5 implemented: Docker infra, Django setup, auth + profile wizard, tours system, bookings + payment adapter; 46 tests passing |

*See `CHANGELOG.md` for full commit-by-commit history. See `ROADMAP.md` for upcoming phases.*
