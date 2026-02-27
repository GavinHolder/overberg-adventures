# Roadmap — Overstrand Adventures PWA

Status key: `[ ]` Not started · `[~]` In progress · `[x]` Complete

---

## Completed

- [x] **Phase 1** — Docker infrastructure (Traefik, Portainer, Redis, App stacks)
- [x] **Phase 2** — Django project restructure (settings, 10 app skeletons, Celery)
- [x] **Phase 3** — Authentication (email OTP, Google/Facebook OAuth, 5-step profile wizard)
- [x] **Phase 4** — Tours system (ActivityCategory, Tour, ItineraryItem, TourCodeWord, seed data)
- [x] **Phase 5** — Bookings + Payment adapter (RSVP flow, capacity enforcement, adapter ABC)

---

## Upcoming

### Phase 6 — PWA Core Screens
Build all PWA-facing templates with pixel-perfect match to the 15 UI reference screenshots.

- [ ] **Task 15** — Base template + bottom nav + PWA shell
  - `templates/base_app.html` (vendor assets from CDN or local static)
  - `static/manifest.json` (PWA installability)
  - `static/js/service-worker.js` (cache-first, offline fallback)
  - Bootstrap 5.3 vendor files in `static/vendor/`

- [ ] **Task 16** — Home screen
  - No-tours state: logo, "Welcome [Name]", tour code entry form
  - With-tours state: "My Tours" list with status badges (RSVP Pending / Confirmed / Completed)
  - HTMX tour code lookup + join flow

- [ ] **Task 17** — Itinerary viewer
  - Satellite map banner (Google Maps embed or static image placeholder until Phase 7)
  - RSVP status banner
  - Day-grouped activity timeline cards (category colour + icon, time, duration, difficulty badge)

- [ ] **Task 18** — Map tab (full-screen)
  - Full-screen Google Maps satellite view placeholder
  - Activity markers (colour-coded circles by category)
  - "View Itinerary" pull-up drawer

- [ ] **Task 19** — Profile tab
  - Orange header card with avatar + name + role
  - Personal details section (read + edit)
  - Health info section
  - Personal notes
  - Settings tab (Location + Notification toggles)

- [ ] **Task 20** — SOS screen
  - Emergency call button
  - Live GPS share link
  - Emergency contacts list
  - All SOS options toggleable by superuser

---

### Phase 7 — Google Maps Integration
Full Google Maps JavaScript API v3 integration.

- [ ] GCP project setup + API key (restricted to domain/IP)
- [ ] Satellite view as default for all map instances
- [ ] Activity markers — colour-coded circles by category; info windows on tap
- [ ] Tour area polygon overlay (stored as GeoJSON in `Tour.polygon`)
- [ ] Walking/driving route polyline from `MapRouteWaypoint` ordered points
- [ ] Admin map drawing UI — draw polygons and plan routes visually (Leaflet.draw or Maps Drawing API)

---

### Phase 8 — Push Notifications
Web Push (PWA-native) with dynamic notification manager.

- [ ] VAPID key generation + `django-webpush` subscription endpoint
- [ ] Service worker push event handler
- [ ] Standard notification triggers: booking confirmation, pre-tour reminder (24 hr + 2 hr)
- [ ] `apps/notifications/tasks.py` — full `send_tour_code_email` implementation via SendGrid
- [ ] Notification manager (backend): create custom notifications, link to bookings/itineraries/users, tag system, time/date scheduling
- [ ] FCM integration for Android Chrome reliability
- [ ] Celery Beat scheduled task for time-based notifications

---

### Phase 9 — Backend Admin Panel (Mobile-Optimised)
Custom Django admin panel, not the default admin. Mobile-first, guide + operator access.

- [ ] Mobile-optimised base template (`templates/admin_panel/`)
- [ ] Tour management: create/edit tours, set parameters, assign guides
- [ ] Itinerary builder: add/reorder activity items, set category/time/location/difficulty
- [ ] User management: view/edit guests, manage roles and permissions
- [ ] Booking management: view RSVPs, confirm/cancel bookings, manual tour code assignment
- [ ] Map drawing interface: draw tour area polygons and route waypoints visually
- [ ] Guide permissions toggle (superuser controls what guides can see)
- [ ] Notification manager UI (see Phase 8)
- [ ] "DEV MODE ACTIVE" banner visible when `DEV_MODE=True`

---

### Phase 10 — Payments (Full Implementation)
Complete the payment adapter scaffolded in Phase 5.

- [ ] `PayFastAdapter` — South African payment gateway integration
- [ ] `PeachPaymentsAdapter` — alternative SA gateway (client to confirm preference)
- [ ] Payment webhook verification (ITN for PayFast, hosted checkout for Peach)
- [ ] Manual payment capture UI in admin panel
- [ ] "Simulate Payment (Paid)" button in DEV_MODE flows
- [ ] Payment confirmation → tour code generated → email sent → booking status → CONFIRMED

---

### Phase 11 — Landing Page + GrapesJS Editor
Separate marketing page from the PWA.

- [ ] `apps/landing/models.py` — `LandingPage` model (rendered HTML/GrapesJS JSON storage)
- [ ] GrapesJS visual page builder integration (client self-editing)
- [ ] Bootstrap 5 marketing page sections: Navbar + logo, hero, feature sections, footer
- [ ] Maintenance/coming-soon mode toggle (`MaintenanceModeMiddleware` real implementation)
- [ ] Landing page on/off toggle from backend

---

### Phase 12 — NFC Check-In
Web NFC API for tour check-in and activity tagging.

- [ ] `apps/nfc/models.py` — `NFCTag` model (booking/activity link)
- [ ] Web NFC API write (guide tags NFC chip with booking ID)
- [ ] Web NFC API read (guest taps → check-in registered)
- [ ] QR code fallback for iOS (Web NFC is Android Chrome only — documented limitation)
- [ ] NFC tap simulation button in DEV_MODE
- [ ] Extensible hook for future payment NFC (Phase 10+ or post-MVP)

---

### Phase 13 — Backup / Restore + Maintenance Mode
Operational reliability features for the deployed VM.

- [ ] `apps/backups/models.py` — `BackupJob` model (scheduled pg_dump, status, S3/local path)
- [ ] Celery Beat task for scheduled database backups
- [ ] Backup download / restore UI in admin panel
- [ ] Maintenance mode toggle (admin UI + `MaintenanceModeMiddleware` final implementation)

---

### Phase 14 — DEV_MODE Overlay + Developer Tools
Complete the developer experience features.

- [ ] Floating DEV MODE button/drawer in all PWA screens
- [ ] "Simulate Payment (Paid)" button on booking flow
- [ ] OTP auto-fill in verify screen
- [ ] NFC tap simulation button
- [ ] Notification preview without FCM
- [ ] All DEV features strictly gated: `settings.DEV_MODE and settings.DEBUG`

---

### Phase 15 — PWA Hardening + Production
Service worker, offline support, and production readiness.

- [ ] Service worker — cache-first strategy for static assets, network-first for API
- [ ] Offline fallback page (shows "You're offline" with cached data where possible)
- [ ] `manifest.json` — icons (192px, 512px), theme colour, display mode, start URL
- [ ] `<meta>` PWA tags for iOS Safari (apple-mobile-web-app-capable, status-bar-style)
- [ ] HTTPS enforcement (Traefik Let's Encrypt — requires domain from client)
- [ ] Production settings hardening (SECURE_HSTS, CSRF_COOKIE_SECURE, SESSION_COOKIE_SECURE)
- [ ] PostgreSQL in production (SQLite only for local dev)
- [ ] Static files on WhiteNoise (local MVP) → S3-compatible storage post-MVP
- [ ] Sentry error tracking integration
- [ ] Performance audit (Lighthouse PWA score target: 90+)

---

## Post-MVP / Future

| Feature | Notes |
|---------|-------|
| Play Store submission | Defer until PWA is live and validated |
| iOS NFC support | Web NFC not supported on iOS — monitor browser support |
| Native app wrapper | Capacitor/Cordova for Play Store if required |
| S3 file storage | Upgrade from local static to S3-compatible after MVP |
| DRF API | Add Django REST Framework if native mobile app needed post-MVP |
| Multi-language | English only for MVP; Afrikaans + Xhosa planned |
| Offline itinerary | Full offline-first support with service worker caching |
| Group bookings | Single booking covering multiple guests |
| Live guide tracking | Real-time GPS share from guide to guests during tour |

---

## Infrastructure Still Pending

| Item | Status |
|------|--------|
| VM IP + SSH credentials | Waiting on client |
| Google Maps GCP project | Not yet created |
| Payment gateway selection | Client to confirm PayFast vs Peach |
| Domain name | IP-based for dev; client to provide domain for HTTPS |
| SendGrid API key | Client to provide |
| VAPID keys | Generate when Phase 8 starts |
