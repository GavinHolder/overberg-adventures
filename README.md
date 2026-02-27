# Overstrand Adventures — PWA Client Project

**Project Type:** Progressive Web App (PWA) — MVP
**Client:** Overstrand Adventures (adventure tourism, Overberg/Kogelberg region, South Africa)
**Stack:** Django 6 · HTMX · Alpine.js · Bootstrap 5 · PostgreSQL
**Started:** 2026-02-27
**Status:** Planning / Design phase

---

## Project Context

Client runs guided adventure tours in the Overstrand/Kogelberg area (Kleinmond, Hermanus, etc.). They have an existing prototype app (`ate-dev.web.app`) that defines the exact look, feel and UX this build must replicate pixel-for-pixel. This is a **PWA-first MVP** — Play Store submission deferred to keep initial costs low.

The app operates on a **tour-code model**: guide creates a tour in the backend → shares a code → guests enter the code to join their itinerary.

---

## UI Reference (plannig/UI/ folder)

All 15 screenshots from client's prototype define the required design. Key screens identified:

| Screen | File(s) | Notes |
|---|---|---|
| Profile Setup Step 1 — Personal Details | 1000220100 | First/Last, Phone(WA), DOB, Email (read-only from social) |
| Profile Setup Step 2 — Health Info | 1000220102 | Fitness 1–5, Medical, Dietary |
| Profile Setup Step 3 — Permissions | 1000220104 | Location + Notification enablement |
| Profile Setup Step 4 — Personal Notes | 1000220106 | Free text, visible to guide |
| Profile Setup Step 5 — Indemnity (scroll) | 1000220108 | Agreement text |
| Indemnity Acceptance Confirmation | 1000220110 | Checkbox + modal confirm |
| Indemnity Modal | 1000220112 | "I Confirm" CTA |
| Home — No Tours | 1000220114 | Logo, Welcome [Name], Tour code entry |
| Tour Join Confirm | 1000220116 | Tour info card + "Join This Trip" |
| Itinerary — Map + Invite Banner | 1000220118 | Satellite map + RSVP + tour metadata |
| Itinerary — Day Timeline | 1000220120 | Day-grouped activity cards with tags/times |
| Home — With Tours | 1000220122 | My Tours list + status badges |
| Map Tab — Full Screen | 1000220126 | Satellite Google Maps, activity markers, "View Itinerary" pull-up |
| Profile Tab — Personal Details | 1000220128 | Orange header card, details, health, notes |
| Profile Tab — Settings | 1000220130 | Location + Notification toggles |

### Design Language
- **Background:** Warm cream `#FAF5EE`
- **Primary:** Orange gradient `#F97316 → #EA580C`
- **Food/Dining accent:** Teal `#0D9488`
- **Cards:** White, `border-radius: 16px`, subtle shadow
- **Nav:** 5-tab bottom bar — Home · Itinerary · SOS · Map · Profile
- **Maps:** Google Maps Satellite view
- **Activity markers:** Colour-coded circles by category (orange=hiking, teal=food)

---

## Client Requirements

### General Features
1. **Social + Email Auth** — Google OAuth, Facebook OAuth, and email/password with email verification (OTP code sent to inbox before account activation)
2. **Google Maps** — Satellite view, polygon drawing for itinerary area highlights, walking/driving route path visualisation; always treat as production-ready
3. **Mobile-first HTMX** — All app screens must be live/reactive, no static page loads within the PWA
4. **Push Notifications** — Web Push (PWA); standard notifications (booking confirmations, pre-tour reminders) + dynamic notification manager where client can create custom notifications linked to individual/grouped bookings, itineraries, or any app entity; tag system for grouping; time/date-based scheduling
5. **NFC** — Web NFC API for check-in/tagging scenarios; payment NFC later; keep extensible
6. **Future:** Client will provide additional feedback over time; scaffold to accommodate

### Frontend (PWA App)
- Exact pixel-match to UI reference screenshots
- Bottom nav: Home, Itinerary, SOS, Map, Profile
- 5-step profile setup wizard (first login)
- Tour-code join flow
- Itinerary viewer (day-grouped timeline, satellite map, activity cards)
- SOS screen (location share, emergency contacts)
- Map tab (full-screen satellite, markers, "View Itinerary" pull-up)
- Profile tab (view/edit details, health, notes, app settings)

### Frontend (Landing Page)
- Separate from PWA; standard Bootstrap 5 marketing page
- Navbar + logo, hero, content sections, footer
- Toggle ON/OFF from backend (maintenance / coming-soon mode)
- **GrapesJS visual page builder** for client self-editing

### Backend (Admin Panel — mobile-optimised)
- Manage: users, bookings, payments, leads, enquiries
- Tour management: create tours, set parameters, manage itinerary items (activities, times, locations, categories, difficulty, duration, distance)
- Map UI: draw polygons and plan routes visually (for tour area definition)
- Itinerary builder with restrictions (age, fitness level, group size, capacity)
- Maintenance mode toggle + landing page toggle
- Backup/restore system
- SendGrid transactional email
- Notification manager (all push notifications managed here)
- Payment gateway — South African (PayFast or Peach Payments)
- Manual payment capture option
- Lead/enquiry pipeline

---

## Tech Stack (Proposed)

| Layer | Technology |
|---|---|
| Backend framework | Django 6.0 |
| API | Django REST Framework |
| Frontend templating | Django Templates + HTMX + Alpine.js |
| CSS framework | Bootstrap 5.3 |
| Database | PostgreSQL (upgrade from SQLite) |
| Auth | django-allauth (Google + Facebook + email) |
| Maps | Google Maps JavaScript API v3 |
| Push notifications | Web Push Protocol + django-webpush + FCM |
| Email | SendGrid (django-anymail) |
| Payments (SA) | PayFast or Peach Payments |
| NFC | Web NFC API (browser-native, Android Chrome) |
| Landing page builder | GrapesJS |
| Background tasks | Celery + Redis |
| Deployment | Docker + Portainer + Traefik |
| File storage | Local (MVP) → S3-compatible later |

---

## App Architecture (High-Level)

```
overberg_adventures/          ← Django project
├── apps/
│   ├── accounts/             ← Auth, profiles, social login, email verification
│   ├── tours/                ← Tour model, itinerary items, tour codes
│   ├── bookings/             ← Bookings, RSVPs, capacity
│   ├── payments/             ← PayFast/Peach, manual capture
│   ├── notifications/        ← Push notifications, notification manager, tags
│   ├── maps/                 ← Polygon storage, route planning
│   ├── nfc/                  ← NFC check-in, tagging
│   ├── landing/              ← GrapesJS landing page, toggle
│   ├── sos/                  ← SOS feature, emergency contacts
│   └── backups/              ← Backup/restore management
├── dashboard/                ← Existing skeleton (repurpose as admin shell)
├── pwa/                      ← PWA manifest, service worker, offline
├── templates/
│   ├── app/                  ← PWA HTMX templates
│   ├── admin_panel/          ← Mobile-optimised backend
│   └── landing/              ← GrapesJS-rendered landing page
└── static/
```

---

## Open Questions / Decisions Needed

1. **Payment gateway**: PayFast vs Peach Payments — PayFast is simpler/cheaper for MVP, Peach has more flexibility. Which does client prefer?
2. **Domain / hosting**: Where is the app deployed? (affects Google Maps API config, OAuth redirect URIs)
3. **SOS screen**: What exactly should SOS do? (Call guide, share GPS location, alert emergency contact, all three?)
4. **Activity categories**: Are hiking/food the only categories, or does client have a full list?
5. **Tour code format**: Client-defined or system-generated? (e.g. "UNLOCK-2026-KLM")
6. **Guide vs Guest roles**: Are guides managed separately? Can guides have the app too, or only admin panel?
7. **NFC hardware**: Does client have specific NFC tags/readers in mind, or is this purely browser-native Web NFC?
8. **Google Maps API key**: Client to provide, or are we setting up a new GCP project?

---

## Key Constraints

- PWA only (no Play Store / App Store for MVP)
- South African market (ZAR payments, +27 phone numbers)
- Mobile-first — all features must work on Android Chrome
- Web NFC is Android Chrome only (not iOS) — document this limitation
- Visual fidelity to prototype is non-negotiable

---

## Development Phases (Draft)

| Phase | Scope |
|---|---|
| 1 | Project scaffold, Docker, PostgreSQL, settings, CI |
| 2 | Auth system (email + Google + Facebook + OTP verification) |
| 3 | Profile setup wizard (5-step) |
| 4 | Tour model + tour code join flow |
| 5 | Itinerary viewer + day timeline |
| 6 | Google Maps integration (satellite, markers, polygons, routes) |
| 7 | SOS feature |
| 8 | Push notifications + notification manager |
| 9 | Backend admin panel (tours, users, bookings) |
| 10 | Payments (PayFast/Peach + manual) |
| 11 | Landing page + GrapesJS builder |
| 12 | NFC check-in |
| 13 | Backup/restore, maintenance mode |
| 14 | PWA manifest, service worker, offline support |
| 15 | QA, performance, production hardening |

---

## Session Log

| Date | Session Summary |
|---|---|
| 2026-02-27 | Initial client brief received; UI reference screenshots reviewed (15 screens); README + design doc created; brainstorming phase |

---

*This README is the source of truth for project context. Update after every significant session.*
