# Overstrand Adventures PWA — System Design

**Date:** 2026-02-27
**Author:** Claude (Brainstorming phase)
**Status:** DRAFT v2 — Questions answered 2026-02-27, pending final approval

---

## 1. Project Overview

Overstrand Adventures is an outdoor adventure tour operator in the Overberg/Kogelberg region of South Africa (Kleinmond, Hermanus, Betty's Bay area). This project delivers a **Progressive Web App** for their guests and a **mobile-optimised admin panel** for their guides and operators.

The core user journey: Guest registers → completes profile → receives a tour code → joins a tour → views itinerary on their phone during the tour.

---

## 2. Design Principles

1. **Pixel-perfect to prototype** — the client's existing `ate-dev.web.app` prototype defines the visual target exactly
2. **Mobile-first always** — every feature designed for a hand in landscape/portrait on Android Chrome
3. **HTMX-driven** — all PWA interactions are partial-page swaps, no SPA framework overhead
4. **Production mindset from day one** — no "dev shortcuts" baked into architecture
5. **Offline-capable** — service worker caches critical views for low-connectivity situations on trail

---

## 3. Design Language (from UI Reference)

### Colour Palette
```
--color-bg:          #FAF5EE   /* warm cream background */
--color-primary:     #F97316   /* orange */
--color-primary-dark:#EA580C   /* orange dark (gradient end) */
--color-secondary:   #0D9488   /* teal (food/dining) */
--color-surface:     #FFFFFF   /* card white */
--color-text:        #1C1917   /* near-black */
--color-text-muted:  #78716C   /* warm grey */
--color-border:      #E7E5E4   /* light border */
--color-danger:      #EF4444   /* SOS/error */
```

### Typography
- Headings: Bold, dark, large (32px+)
- Labels: Small caps, muted, letter-spaced (`font-size: 11px; letter-spacing: 0.08em`)
- Body: 16px, comfortable line-height

### Components
- **Cards:** `border-radius: 16px`, white, `box-shadow: 0 2px 12px rgba(0,0,0,0.06)`
- **Buttons (primary):** Orange gradient, `border-radius: 14px`, full-width on mobile
- **Bottom nav:** 5 tabs — Home · Itinerary · SOS · Map · Profile; active tab bold + icon filled
- **Progress bar (onboarding):** Horizontal step segments, orange = complete, grey = pending
- **Activity markers (map):** Circular coloured badges with category icon (orange=hiking, teal=food)

---

## 4. Application Architecture

### 4.1 Tech Stack

| Concern | Choice | Rationale |
|---|---|---|
| Backend | Django 6.0 | Already started; mature, batteries-included |
| API | Django REST Framework | HTMX needs JSON endpoints for Alpine.js interactions |
| Templating | Django Templates + HTMX | Live partials without SPA complexity |
| Reactivity | Alpine.js (minimal) | Toggle states, modals, form interactions |
| CSS | Bootstrap 5.3 + custom CSS vars | Rapid layout, override with design tokens |
| Database | PostgreSQL | Replaces SQLite; production-grade, geo support |
| Auth | django-allauth | Google + Facebook OAuth + email; battle-tested |
| Maps | Google Maps JS API v3 | Exact match to prototype (satellite view) |
| Push | Web Push + django-webpush + FCM | PWA native push, works on Android Chrome |
| Email | SendGrid via django-anymail | Transactional + marketing |
| Payments | PayFast (primary) | Most common SA gateway, simple integration |
| Tasks | Celery + Redis | Scheduled notifications, async email |
| NFC | Web NFC API | Browser-native on Android Chrome |
| Landing CMS | GrapesJS | Visual drag-drop builder, client self-service |
| Deployment | Docker + Portainer + Traefik | Client's existing infra pattern |

### 4.2 Django App Structure

```
overberg_adventures/
├── apps/
│   ├── accounts/          # User, Profile, social auth, OTP email verification
│   ├── tours/             # Tour, ItineraryItem, ActivityCategory, TourCode
│   ├── bookings/          # Booking, RSVP, capacity management
│   ├── payments/          # Payment, PayFastWebhook, ManualCapture
│   ├── notifications/     # NotificationTemplate, ScheduledNotification, Tag, Subscription
│   ├── maps/              # TourPolygon, RouteWaypoint, MapLayer
│   ├── nfc/               # NFCTag, NFCCheckIn, NFCEvent
│   ├── landing/           # LandingPage (GrapesJS), LandingPageToggle
│   ├── sos/               # SOSEvent, EmergencyContact
│   └── backups/           # BackupJob, BackupRestore
├── pwa/                   # manifest.json, service-worker.js, offline page
├── dashboard/             # (existing skeleton — becomes admin shell app)
├── templates/
│   ├── app/               # PWA HTMX partials
│   ├── admin_panel/       # Mobile-optimised backend
│   └── landing/           # Public landing page
└── static/
    ├── css/               # Custom CSS, Bootstrap overrides
    ├── js/                # Alpine.js, HTMX, GrapesJS, Maps init
    └── icons/             # PWA icons, activity category icons
```

---

## 5. Core Data Models (Summary)

### accounts.UserProfile
```
user (OneToOne → User)
avatar, first_name, last_name, phone_whatsapp, date_of_birth
fitness_level (1–5), medical_conditions (text), dietary_requirements (text)
personal_notes (text)
indemnity_accepted (bool), indemnity_accepted_at (datetime)
email_verified (bool)
role: GUEST | GUIDE | OPERATOR | ADMIN
```

### tours.Tour
```
name, description, slug
tour_code (unique, e.g. "OVERSTRAND-UNLOCKED")
guide (FK → User)
start_datetime, location_name, location_lat, location_lng
capacity (int), status: DRAFT | ACTIVE | COMPLETED | CANCELLED
polygon (GeoJSON stored as JSONField)
restrictions: min_fitness, max_age, etc.
```

### tours.ItineraryItem
```
tour (FK), day (int), order (int)
title, description
activity_category (FK → ActivityCategory)
start_time, duration_minutes
location_name, location_lat, location_lng
difficulty: EASY | MODERATE | HARD
distance_km (optional)
```

### bookings.Booking
```
tour (FK), user (FK)
status: INVITED | RSVP_PENDING | CONFIRMED | CANCELLED
invited_at, rsvp_deadline, confirmed_at
spots_held (int)
```

### notifications.NotificationTemplate
```
name, body_template (text with variables)
trigger_type: BOOKING_CONFIRMATION | PRE_TOUR_REMINDER | CUSTOM
tags (M2M → NotificationTag)
```

### notifications.ScheduledNotification
```
template (FK), created_by (FK → User)
target: ALL_BOOKINGS | SPECIFIC_BOOKING | SPECIFIC_TOUR | SPECIFIC_USER
target_ids (JSONField)
send_at (datetime), sent_at (datetime, null)
status: PENDING | SENT | FAILED
tags (M2M)
```

---

## 6. Screen-by-Screen Specification

### 6.1 Auth Flow
- **Login/Signup page:** Three options: "Continue with Google", "Continue with Facebook", "Use Email"
- **Email signup:** Email → OTP code sent via SendGrid → Enter code → Profile setup wizard
- **Social login:** OAuth callback → if new user → Profile setup wizard; if returning → Home
- **Email verified badge:** Once OTP confirmed, `email_verified = True`, no re-verification needed

### 6.2 Profile Setup Wizard (5 Steps)
1. **Personal Details** — First name, Last name, Phone (+27 format), DOB (dropdown), Email (read-only)
2. **Health Information** — Fitness level (1–5 selector), Medical conditions, Dietary requirements
3. **App Permissions** — Location (Web Geolocation API prompt), Notifications (Web Push permission prompt)
4. **Personal Notes** — Free-text note visible to guide
5. **Indemnity Agreement** — Scrollable legal text, checkbox + confirmation modal → "Complete Profile"

Progress bar at top: 5 orange segments, filling as steps complete. HTMX partial swaps per step.

### 6.3 Home Screen
- **State A (no tours):** Logo centred, "Welcome, [Name]", tour code input + "Discover" button, footer copyright
- **State B (has tours):** Same header, "MY TOURS" section with cards showing tour name, status badge (COMPLETED/UPCOMING), tour type badge (UNLOCK/etc.), date+time

### 6.4 Tour Code Join Flow
1. User enters code → HTMX POST to `/tours/join/` → returns tour preview card
2. Card shows: Tour name, date, location, user profile summary, "Join This Trip" CTA + Cancel
3. On confirm: Booking created, redirect to Itinerary view

### 6.5 Itinerary View
- Top half: Satellite Google Map with activity markers
- "You're Invited!" invite banner (if RSVP pending, with countdown + spots remaining)
- Tour metadata: name, RSVP button, activities count, start datetime + status, location + Directions link, Guide name + Contact (WhatsApp link)
- Day-grouped timeline: Day header (collapsible) → activity cards
  - Activity card: Category icon circle, title, location, time badge, difficulty/duration, distance (if hike), category tag pill

### 6.6 Map Tab
- Full-screen Google Maps satellite view
- Activity markers plotted (same colour-coded circles)
- Walking route polylines (green) / driving route polylines (blue) if configured
- Tour area polygon overlay (semi-transparent orange fill, orange stroke)
- Bottom pill: "View Itinerary" → slides up itinerary panel (Alpine.js drawer)
- Left controls: Zoom +/−, layer toggle, locate me, compass

### 6.7 SOS Screen
- Large red SOS button (tap → confirms → sends location + alert)
- Emergency contact list (added in profile)
- Guide contact shortcut
- Current GPS coordinates display
- Pre-tour: configure emergency contacts; during tour: one-tap alert

### 6.8 Profile Tab
- Orange gradient banner header card (avatar circle, name, role "Guest Traveller", Edit Profile button)
- Personal Details section (Name, DOB+age+star sign, Phone, Email)
- Health & Diet section (Fitness level, Medical, Dietary)
- Notes section (Personal notes)
- App Settings section (Location toggle, Notifications toggle)

---

## 7. Google Maps Integration

### Requirements from Client
- Satellite base map (same as prototype)
- Activity location markers (colour-coded by category)
- Polygon drawing for tour area boundaries
- Walking route path visualisation (polyline)
- Driving route path visualisation (polyline, different colour)

### Implementation
- **API Key:** Client must provide GCP project with Maps JS API + Directions API enabled
- **Map initialisation:** HTMX page loads map container, Alpine.js init fires `initMap()`
- **Markers:** Custom circular SVG markers rendered per activity category
- **Polygons:** Stored as GeoJSON in `TourPolygon.geometry` (JSONField); rendered via `google.maps.Polygon`
- **Routes:** Stored as ordered `RouteWaypoint` records; rendered via `google.maps.Polyline` or Directions API
- **Admin polygon editor:** Backend uses Google Maps Drawing Library (`google.maps.drawing.DrawingManager`)
- **Admin route planner:** Click-to-add waypoints, drag to reorder, Directions API preview

### Required from Client
- Google Cloud Platform project
- Maps JavaScript API key (restricted to domain)
- Directions API enabled
- (Optional later) Places API for location search

---

## 8. Push Notifications Architecture

### Standard Notifications (auto-triggered)
| Trigger | Notification |
|---|---|
| Booking confirmed | "Your spot on [Tour] is confirmed for [Date]" |
| RSVP invited | "You've been invited to [Tour] — [X] spots left, expires [Time]" |
| 24h before tour | "Tomorrow: [Tour] starts at [Time] at [Location]" |
| 2h before tour | "Get ready! [Tour] starts soon. Your guide is [Name]" |
| Tour started | "Your tour has started — check your itinerary" |
| Activity starting | "[Activity] starts in 15 minutes at [Location]" |

### Dynamic Notification Manager (Admin)
- Create custom notification with: title, body (with variable tags), icon
- Set target: all bookings on tour X / specific users / specific booking / tag group
- Set schedule: immediate / specific datetime / relative to tour start
- Tag system: group notifications by tags (e.g. "whale-season", "hiking-group-a")
- Preview before send
- Send history + delivery status

### Tech: Web Push
- Browser subscribes → `PushSubscription` stored in DB
- Celery beat checks `ScheduledNotification` every minute → sends via Web Push Protocol
- FCM as push service for Android Chrome
- django-webpush handles subscription management + vapid keys
- Service worker `push` event handler → shows `showNotification()`

---

## 9. NFC Architecture

### Phase 1 (MVP)
- Web NFC API (`NDEFReader`) — Android Chrome only
- **Check-in use case:** Guide writes tour ID to NFC tag → Guest taps phone → app reads tag → logs check-in event
- `NFCCheckIn` model: user, tour, tag_id, timestamp, location (GPS at tap time)
- Profile permissions step already requests location; NFC permission requested at first scan
- Graceful fallback UI for non-NFC devices (QR code scan alternative)

### Phase 2 (Future)
- NFC payment integration (client to specify gateway/hardware)
- NFC-based activity completion logging
- Guide NFC wristband/badge scanning

### iOS Limitation
- Web NFC is Android Chrome only — document clearly; iOS users use QR fallback

---

## 10. Backend Admin Panel

### Mobile-optimised admin (not Django default admin)
Custom-built with Bootstrap 5, designed to work on phone screen:

**Sections:**
1. **Dashboard** — Today's tours, upcoming tours, recent signups, revenue today
2. **Tours** — List, Create, Edit (with map polygon + route planner embedded)
3. **Itinerary Builder** — Drag-drop day/activity ordering
4. **Bookings** — Filter by tour, status; RSVP management; capacity view
5. **Users** — Search, view profile, edit, deactivate
6. **Payments** — List payments, mark manual payments, refund notes
7. **Leads & Enquiries** — CRM-lite pipeline
8. **Notifications** — Notification manager (create/schedule/tag)
9. **Landing Page** — GrapesJS editor embed + ON/OFF toggle
10. **Settings** — Maintenance mode toggle, SendGrid config, payment gateway keys
11. **Backups** — Manual backup trigger, restore, automated schedule log

---

## 11. Landing Page

- Standard Bootstrap 5 marketing page (NOT HTMX — static content)
- Sections: Navbar (logo + nav links), Hero (fullwidth image/video + CTA), About, Tours overview, Gallery, Contact form, Footer
- GrapesJS embedded in admin panel → client edits blocks visually → saved as HTML/CSS to DB → rendered on `/`
- **Toggle:** `LandingPage.is_enabled` flag in DB; when OFF → show maintenance/coming-soon page
- **Maintenance mode:** Separate flag; when ON → all URLs except admin redirect to maintenance page

---

## 12. Payments

### Primary: PayFast
- South African, supports credit card, EFT, SnapScan, Zapper, Mobicred
- ITN (Instant Transaction Notification) webhook → updates `Payment.status`
- Sandbox available for testing

### Manual Capture
- Admin captures: amount, reference, method (EFT/cash), date, notes → `ManualPayment` record
- Links to booking → marks booking as paid

### Payment flow
1. Guest RSVPs → booking created (PENDING)
2. Payment initiated via PayFast redirect or admin manual capture
3. Webhook/admin confirms → booking status → CONFIRMED
4. Push notification + confirmation email sent via SendGrid

---

## 13. PWA Configuration

### manifest.json
```json
{
  "name": "Overstrand Adventures",
  "short_name": "OA Tours",
  "theme_color": "#F97316",
  "background_color": "#FAF5EE",
  "display": "standalone",
  "orientation": "portrait",
  "start_url": "/app/",
  "icons": [...]
}
```

### Service Worker
- Cache-first for static assets
- Network-first for API/HTMX calls
- Offline fallback page for lost connectivity
- Push event handler for notifications
- Background sync for SOS event queuing (if offline)

---

## 14. Security Considerations

### Authentication
- OAuth state parameter validated (CSRF protection)
- Email OTP: 6-digit code, 15-minute expiry, max 3 attempts
- JWT not used — session-based auth (django sessions + CSRF)

### Data
- User health data encrypted at rest (Django field encryption)
- Indemnity acceptance timestamped + immutable
- Phone numbers stored hashed for lookup only

### API
- All HTMX endpoints require `@login_required`
- Rate limiting on auth endpoints (django-ratelimit)
- CSRF tokens on all mutating requests (HTMX `hx-headers`)

---

## 15. Open Questions — RESOLVED (2026-02-27)

| # | Question | Answer |
|---|---|---|
| 1 | Payment gateway | **Payment-gateway agnostic scaffolding** — client to provide details later; PayFast/Peach/manual all plug in via adapter pattern |
| 2 | Domain/hosting | **IP-based for now** — local VM (dev), client will provide IP + SSH credentials |
| 3 | SOS behaviour | **All options, each toggleable** — guide alert, emergency contact ping, live GPS link share; superuser controls which are active |
| 4 | Activity categories | **Fully dynamic** — client manages in backend; seed script provides initial set (hiking, food & dining, kayaking, cycling, scenic drive, whale watching, swimming, photography, cultural) |
| 5 | Tour code format | **Random memorable word** — sent via email on payment confirmation; seed from nature/Overberg word list |
| 6 | Google Maps | **Set up from scratch** — new GCP project to create |
| 7 | Guide app access | **Both PWA + admin panel** — superuser has toggleable permissions per guide role (what they can see: participant health, contact details, notes, financial info etc.) |
| 8 | Group size | TBD — scaffold for it, not required for MVP |
| 9 | NFC hardware | TBD — client hasn't purchased yet; scaffold Web NFC API |
| 10 | Languages | English only for MVP |

## 15b. New Requirements (2026-02-27)

### Tour Code System
- Format: **single randomly generated memorable word** (e.g. nature/Overberg themed: "fynbos", "pelican", "milkwood", "protea", "renosterveld", "klipspringer")
- Word list curated from Overberg/Kogelberg flora, fauna, landmarks — stored in DB as `TourCodeWord` model for client management
- Delivery: sent via SendGrid email upon payment confirmation
- Dev mode: "Simulate Payment" button in payment management section → triggers same flow (code generated + email sent or displayed on screen)

### Developer Mode Toggle
- Global `DEV_MODE` setting (env var + DB flag for runtime toggle without restart)
- When ON, unlocks:
  - **"Simulate Payment (Paid)"** button on any pending payment → auto-confirms + triggers tour code email
  - **Bypass email OTP** — OTP shown in UI (or auto-filled) instead of requiring real email
  - **Bypass OAuth** — simple username/password login without Google/Facebook
  - **Skip payment step** on booking flow
  - **Notification preview** — push notification appears in UI without going through FCM
  - **NFC simulation** — button to simulate an NFC tap with a tag ID
- DEV_MODE only available when `DEBUG=True` (hard safety guard)
- Admin panel shows a visible "DEV MODE ACTIVE" banner when enabled

### Infrastructure: VM Setup

**Target:** Client-provided VM (IP + SSH credentials to be provided)

**Stack layout (separate Docker Compose stacks in Portainer):**

| Stack | Services |
|---|---|
| `traefik` | Traefik reverse proxy (handles routing, SSL via self-signed or Let's Encrypt) |
| `portainer` | Portainer CE (Docker management UI) |
| `redis` | Redis (Celery broker + cache) |
| `app` | Django app — client deploys manually from GitHub repo |

**SSH setup:**
1. Connect with provided credentials
2. Generate key pair on dev machine: `ssh-keygen -t ed25519`
3. Add public key to VM `~/.ssh/authorized_keys`
4. Configure `~/.ssh/config` on dev machine for passwordless access
5. Disable password auth on VM SSH daemon (`PasswordAuthentication no`)

**Docker Compose files:** Created as separate files per stack, committed to a `deploy/` folder in the repo.

### Payment Gateway Adapter Pattern

```python
# apps/payments/adapters/base.py
class PaymentGatewayAdapter(ABC):
    @abstractmethod
    def create_payment(self, booking, amount) -> PaymentSession: ...
    @abstractmethod
    def verify_webhook(self, request) -> WebhookResult: ...
    @abstractmethod
    def refund(self, payment_id, amount) -> RefundResult: ...

# apps/payments/adapters/payfast.py
class PayFastAdapter(PaymentGatewayAdapter): ...

# apps/payments/adapters/peach.py
class PeachPaymentsAdapter(PaymentGatewayAdapter): ...

# apps/payments/adapters/manual.py
class ManualPaymentAdapter(PaymentGatewayAdapter): ...

# apps/payments/adapters/dev.py  (DEV_MODE only)
class DevSimulateAdapter(PaymentGatewayAdapter): ...
```

Active adapter configured via `PAYMENT_GATEWAY=payfast|peach|manual` env var.

---

## 16. Proposed Development Approach

### Option A: Monolith-first (RECOMMENDED)
Single Django project, all apps co-located. HTMX handles all interactivity. No separate API service. Simplest to deploy, easiest for a solo/small team, fastest to MVP.

**Trade-offs:** If later they want a native app, would need to add DRF API layer. That's straightforward to add post-MVP.

### Option B: Django API + Separate React Frontend
DRF backend + React PWA. Better long-term for native app pivot. More complex now, slower to MVP, more DevOps overhead.

### Option C: Django + Nuxt/Next PWA
Middle ground. Still adds frontend complexity vs HTMX.

**Recommendation: Option A.** HTMX + Alpine.js + Django Templates is the right tool for this use case. Extremely capable for a tour app. Can add DRF layer for native app later if client decides to invest in Play Store.

---

## Approval Status

- [x] Architecture approved (monolith-first)
- [x] Tech stack approved
- [x] Screen specifications approved
- [x] Open questions answered (2026-02-27)
- [x] Tour code format confirmed: single word, Overberg/nature themed
- [x] Ready to proceed to implementation planning

---

*Next step: Address open questions, get user approval, then invoke `writing-plans` skill to create phased implementation plan.*
