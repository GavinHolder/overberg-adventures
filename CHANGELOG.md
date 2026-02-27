# Changelog

All notable changes to Overstrand Adventures PWA are documented here.
Format: `[date] type: description — files affected`

---

## 2026-02-27

### Infrastructure

**feat: Docker stacks — Traefik, Portainer, Redis, App** `a9b1eda`
- `deploy/traefik/docker-compose.yml` + `traefik.yml` — Traefik v3.1 reverse proxy, `traefik_net` bridge network owner
- `deploy/portainer/docker-compose.yml` — Portainer CE 2.21.4 container management
- `deploy/redis/docker-compose.yml` — Redis 7-alpine with AOF persistence and healthcheck
- `deploy/app/docker-compose.yml` — App stack: web + postgres:16 + celery + celery-beat, all services join `traefik_net`
- `Dockerfile` — python:3.12-slim, non-root `app` user, gunicorn entrypoint
- `entrypoint.sh` — runs migrate + collectstatic before starting gunicorn
- `.env.example` — all required env vars documented with production warnings
- `.dockerignore` — excludes secrets, cache, media from build context
- `deploy/SSH_SETUP.md` — ed25519 key setup, SSH tunnel instructions for dashboard access

**fix: Secure Docker infra** `774120a`
- `deploy/traefik/docker-compose.yml` — Traefik dashboard restricted to `127.0.0.1:8080` (SSH tunnel only)
- `deploy/portainer/docker-compose.yml` — Portainer restricted to `127.0.0.1:9000`, image pinned from `latest` to `2.21.4`
- `Dockerfile` — collectstatic moved from build-time to `entrypoint.sh` to avoid missing-env failures in CI
- Non-root `app` user added to container

---

### Django Project Setup

**feat: Django restructure — settings, 10 app skeletons, Celery** `9c83812`
- `requirements.txt` — Django 6.0.2, psycopg2, decouple, whitenoise, gunicorn, allauth 65.3, anymail/sendgrid, celery, django-celery-beat, redis, django-webpush, django-ratelimit, debug-toolbar, pytest-django, pytest-cov
- `overberg_adventures/settings.py` — full rewrite: python-decouple for all env vars, `DEV_MODE = config(...) and DEBUG` (double-guarded), `TIME_ZONE = 'Africa/Johannesburg'`, WhiteNoise, allauth social providers, anymail/SendGrid, Celery/Redis, debug-toolbar conditional on DEBUG
- `overberg_adventures/celery.py` + `__init__.py` — Celery app with `autodiscover_tasks`
- `pytest.ini` — `DJANGO_SETTINGS_MODULE` configured
- 10 app skeletons created: `accounts`, `tours`, `bookings`, `payments`, `notifications`, `maps`, `nfc`, `landing`, `sos`, `backups`
- Each skeleton: `apps.py`, `models.py`, `views.py`, `urls.py`, `admin.py`, `tests/__init__.py`, `migrations/__init__.py`
- `apps/landing/middleware.py` — `MaintenanceModeMiddleware` placeholder (pass-through until Phase 10)
- `apps/accounts/context_processors.py` — `dev_mode` context processor injected into all templates

---

### Phase 3: Authentication System

**feat: Auth system — EmailOTP, UserProfile, login/OTP views, 5-step profile wizard** `b33909a`

**Models (`apps/accounts/models.py`):**
- `EmailOTP` — 6-digit code, 15-minute expiry, 3-attempt lockout, `EmailOTPManager.create_for_user()` deletes previous unverified OTPs before creating new one
- `UserProfile` — auto-created via `post_save` signal on User; Role choices (GUEST/GUIDE/OPERATOR/ADMIN); personal fields (first/last name, phone_whatsapp, date_of_birth, avatar); health fields (fitness_level 1–5, medical_conditions, dietary_requirements); wizard fields (personal_notes, indemnity_accepted + timestamp, location_enabled, notifications_enabled); `setup_complete`, `full_name`, `initials` properties

**Views (`apps/accounts/views.py`):**
- `login_page` — Google/Facebook/email tabs; DEV_MODE bypass login
- `email_signup` — creates User + triggers OTP email; stores OTP in session if DEV_MODE
- `verify_otp` — 6-digit validation, lockout after 3 attempts, expiry check
- `dev_login` — simple username/password, only active when DEV_MODE=True
- `profile_setup` — wizard shell, redirects completed profiles to home
- `profile_setup_step` — HTMX-powered step handler (steps 1–5)
- `profile_settings_toggle` — Location/Notification permission toggles
- `logout_view` — standard allauth logout

**Emails (`apps/accounts/emails.py`):**
- `send_otp_email(user, code)` — SendGrid transactional email via django-anymail

**Templates:**
- `templates/base_app.html` — Bootstrap 5.3 CDN, HTMX, Alpine.js, dev banner, bottom nav, PWA manifest link
- `templates/app/partials/bottom_nav.html` — 5-tab bottom nav with SVG icons (Home/Itinerary/SOS/Map/Profile), avatar initials
- `templates/accounts/login.html` — Google + Facebook OAuth buttons, email tab, DEV_MODE login panel
- `templates/accounts/verify_otp.html` — 6-digit OTP inputs with Alpine.js auto-advance, DEV_MODE OTP display
- `templates/accounts/setup/wizard.html` — HTMX step shell with progress bar
- `templates/accounts/setup/step1_personal.html` — First/Last name, WhatsApp phone, DOB, email (read-only)
- `templates/accounts/setup/step2_health.html` — Fitness 1–5 selector, medical conditions, dietary requirements
- `templates/accounts/setup/step3_permissions.html` — Location + Notification enable buttons
- `templates/accounts/setup/step4_notes.html` — Personal notes textarea (visible to guide)
- `templates/accounts/setup/step5_indemnity.html` — Scrollable indemnity text, Alpine.js confirmation modal

**CSS (`static/css/app.css`):**
- Design token system: `--color-bg: #FAF5EE`, `--color-primary: #F97316`, `--color-primary-dark: #EA580C`, `--color-secondary: #0D9488`
- Component classes: `.btn-oa-primary`, `.btn-oa-outline`, `.card-oa`, `.form-control-oa`, `.otp-input`, `.fitness-btn`, `.bottom-nav`, `.dev-banner`, `.progress-steps`, `.avatar-sm`

---

### Phase 4: Tours System

**feat: Tours app — ActivityCategory, Tour, ItineraryItem, TourCodeWord, seed commands** `3dd1baa`

**Models (`apps/tours/models.py`):**
- `ActivityCategory` — name, icon (Bootstrap Icons), colour (hex), is_active, order; ordering `['order', 'name']`; 10 initial categories seeded
- `TourCodeWord` — pool of Overberg/nature single-word tour codes; `generate()` classmethod
- `Tour` — name, tour_code (unique), description, guide FK, start/end datetime, location (name/lat/lng), capacity, status (DRAFT/ACTIVE/COMPLETED/CANCELLED), polygon (JSONField for GeoJSON), fitness/age restrictions, RSVP deadline hours; `spots_remaining` + `is_full` properties
- `ItineraryItem` — tour FK, day, order, title, category FK, start_time, duration_minutes, location, difficulty (EASY/MODERATE/HARD), distance_km; ordering `['day', 'order']`; `duration_display` property
- `MapRouteWaypoint` — tour FK, route_type (WALKING/DRIVING), ordered lat/lng waypoints

**Management commands:**
- `seed_categories` — seeds 10 initial activity categories (Hiking, Food & Dining, Kayaking, Cycling, Scenic Drive, Whale Watching, Swimming, Photography, Cultural, Accommodation)
- `seed_tour_codes` — seeds 54 unique Overberg/nature words (fynbos, pelican, milkwood, protea, klipspringer, etc.)

**fix: Add tour_code field + fix ItineraryItem ordering** `d2cfa4e`
- `Tour.tour_code` field missing from initial commit — added
- `ItineraryItem.Meta.ordering` had spurious `start_time` field — removed

**fix: Tours app quality** `bbdf3b0`
- `TourCodeWord.generate()` — wrapped in `transaction.atomic()` + `select_for_update()` to prevent concurrent tour code double-assignment
- `seed_tour_codes.py` — removed 4 duplicate words from source list, removed `dict.fromkeys()` workaround
- `ItineraryItem.category` FK — added `related_name='itinerary_items'` consistent with project conventions
- `test_tour_spots_remaining_with_bookings` — replaced inert placeholder with Phase 5 skip marker

---

### Phase 5: Bookings + Payment Adapter

**feat: Booking model with capacity validation and RSVP flow** `3abc62b`

**Model (`apps/bookings/models.py`):**
- `Booking` — Status choices (INVITED/RSVP_PENDING/CONFIRMED/CANCELLED), tour FK + user FK with `unique_together`, tour_code field (assigned after payment), invited_at, rsvp_deadline, confirmed_at
- `BookingManager.create_from_rsvp(user, tour)` — capacity check + create in one call

**Tour model updated (`apps/tours/models.py`):**
- `spots_remaining` — now queries `self.bookings.filter(status__in=['RSVP_PENDING', 'CONFIRMED']).count()`; `hasattr` guard removed
- `is_full` — delegates to `spots_remaining <= 0`

**feat: Payment adapter pattern** `ebd769d`
- `apps/payments/adapters/base.py` — `PaymentGatewayAdapter` ABC (create_payment_session, verify_webhook, process_confirmation) + `PaymentResult` dataclass
- `apps/payments/adapters/__init__.py` — `get_payment_adapter()` factory dispatching on `PAYMENT_GATEWAY` + `DEV_MODE`
- `apps/payments/adapters/manual.py` — `ManualPaymentAdapter`: admin-captured payments, no webhook
- `apps/payments/adapters/dev.py` — `DevSimulateAdapter`: `simulate_payment()` instantly confirms booking
- `apps/payments/adapters/payfast.py` + `peach.py` — stubs raising `NotImplementedError` (scaffold for Phase 10)
- `apps/notifications/tasks.py` — `send_tour_code_email` Celery task placeholder

**fix: Atomic booking capacity, DEV_MODE guard, on_commit email** `2d2fb92`
- `BookingManager.create_from_rsvp` — wrapped in `transaction.atomic()` + `select_for_update()` on tour row to prevent overbooking under concurrent load
- `get_payment_adapter()` — `gateway == 'dev'` branch now also requires `DEV_MODE=True`; previously allowed DevSimulateAdapter in production if env var was misconfigured
- `process_confirmation` (both manual + dev adapters) — `send_tour_code_email.delay()` wrapped in `transaction.on_commit()` to prevent task firing before DB commit is durable
- Status assignments use `Booking.Status.CONFIRMED` enum (not raw strings)

---

## Test Coverage Summary (as of 2026-02-27)

| App | Tests | Status |
|-----|-------|--------|
| accounts | auth models, OTP, UserProfile, views | passing |
| tours | ActivityCategory, Tour, ItineraryItem, TourCodeWord, seed commands | passing |
| bookings | RSVP flow, capacity enforcement, uniqueness, spots_remaining | passing |
| payments | adapter factory, manual confirm, dev simulate, webhook guard | passing |
| **Total** | **46 tests** | **46 passed, 0 failed** |
