# Roadmap — Overstrand Adventures PWA

Status key: `[ ]` Not started · `[~]` In progress · `[x]` Complete

---

## Completed

- [x] **Phase 1** — Docker infrastructure (Traefik, Portainer, Redis, App stacks)
- [x] **Phase 2** — Django project restructure (settings, 10 app skeletons, Celery)
- [x] **Phase 3** — Authentication (email OTP, Google/Facebook OAuth, 5-step profile wizard)
- [x] **Phase 4** — Tours system (ActivityCategory, Tour, ItineraryItem, TourCodeWord, seed data)
- [x] **Phase 5** — Bookings + Payment adapter (RSVP flow, capacity enforcement, adapter ABC)
- [x] **Phase 6** — PWA Core Screens (Tasks 15-22 complete, 57 tests passing)

---

## Upcoming

### Phase 6 — PWA Core Screens ✅ COMPLETE

- [x] **Task 15** — PWA assets + base_app.html blocks
  - `static/manifest.json` · `static/js/service-worker.js` (network-first)
  - SW served from root `/service-worker.js` via Django view (correct scope)
  - `{% block main_class %}` + `{% block bottom_nav %}` template overrides

- [x] **Task 16** — URL wiring + stub views
  - All PWA routes wired; `LOGIN_REDIRECT_URL = '/'`; SPA shell templates

- [x] **Task 17** — Home screen
  - No-tours state: logo, "Welcome [Name]", tour code entry form
  - With-tours state: "My Tours" list with status badges
  - SPA shell + `home_hero.html` + `home_tour_list.html` + `tour_card.html` partials

- [x] **Task 18** — Tour code join flow
  - POST lookup → redirect to confirm page → POST creates Booking
  - SPA shell + `join_header.html` + `join_user_card.html` partials

- [x] **Task 19** — Itinerary screen
  - Day-grouped timeline (sorted by `item.day` integer); Alpine.js collapsible sections
  - RSVP status banner (INVITED / RSVP_PENDING states); Google Maps placeholder banner
  - SPA shell + `itinerary_header.html` + `itinerary_day.html` + `activity_item.html` partials
  - Hex colour validator on `ActivityCategory.colour`

- [x] **Task 20** — SOS screen
  - WhatsApp deep-link with GPS coords to guide (`navigator.geolocation`, `escapejs` XSS guard)
  - SA emergency numbers: SAPS 10111 · Ambulance 10177 · NSRI · Mountain Rescue · Fire · 112
  - Offline First Aid guides: Snake Bite, Broken Bone, Heart Attack, Fainting, Drowning, Burns
  - Confirmation dialogs before all calls/sends; 10s geolocation timeout
  - `SosConfig` singleton + `EmergencyContact` model; all sections admin-toggleable

- [x] **Task 21** — Map screen
  - Full-screen container; activates Google Maps JS when `GOOGLE_MAPS_API_KEY` set
  - Satellite view default, zoom 13; dark-green placeholder when no key
  - "VIEW ITINERARY" pill button when active booking present

- [x] **Task 22** — Profile screen
  - Orange gradient header card: avatar/initials, full name, role display, Edit Profile link
  - Personal details, Health & Diet, Notes, App Settings (HTMX-wired toggles)
  - SPA shell + 5 partials; DEV MODE banner

---

### Phase 7 — Google Maps Integration
Full Google Maps JavaScript API v3 integration.

- [ ] GCP project setup + API key (restricted to domain/IP)
- [ ] Satellite view as default for all map instances
- [ ] Activity markers — colour-coded by category; info window (title, time, location) on tap
- [ ] GPS coordinate picker modal in itinerary builder (admin side)
- [ ] Tour area polygon overlay (stored as GeoJSON in `Tour.polygon`)
- [ ] Walking/driving route polyline from `MapRouteWaypoint` ordered points
- [ ] Admin map drawing UI — draw polygons and plan routes visually (Maps Drawing API)
- [ ] Guest GPS location sharing — opt-in toggle; sends real-time coords to guide's manifest view
- [ ] Live guest map (guide side) — see all opted-in guests as pins on map during active tour

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
- [ ] Smart schedule alerts — "Your next activity starts in 15 minutes" via Celery + push (based on itinerary times)

---

### Phase 9 — Guide Dashboard (Mobile-Optimised Admin Panel)
Custom mobile-first dashboard for guides and operators. Not the default Django admin.
4 management tabs: Tours · Activities · Guests · Guides

- [ ] Mobile-optimised base template (`templates/admin_panel/`)
- [ ] **Tours tab** — create/edit/delete tours; tour cards (name, dates, guest count, activity count, status)
  - QR code generation per tour (scannable + shareable join URL)
  - Map Picker modal for GPS coordinate input on tour/activity items
  - Cascading delete (itinerary items, bookings, photos)
  - Tour Templates — clone an existing tour for repeat routes
- [ ] **Itinerary Builder** (per tour) — add/edit/delete/reorder activity items
  - Hierarchical: Activities → Steps/Checkpoints as parent-child
  - Drag-to-reorder by day and time (HTMX + Alpine.js sortable)
  - GPS coordinate picker per stop (integrates Phase 7 map picker)
- [ ] **Activities tab** — Activity Library: reusable templates (e.g., "Shark Cage Diving", "Wine Tasting")
  - Create/edit/delete activity templates; name, description, category, type, icon, pricing info
  - Custom activity type creation
  - Activity Picker modal for itinerary builder
- [ ] **Guests tab** — aggregated guest list across all tours
  - Guest Manifest per tour: enrollment status, RSVP/attendance tracking, medical/dietary/contact info
  - Edit guest details; delete guest (atomic removal); promote guest to assistant-guide role
  - Attendance confirmation counts (headcount without manual roll call)
- [ ] **Guides tab** — list/edit/delete guide accounts; role management (admin, lead-guide, guide, assistant, partner, host)
  - Multi-guide assignment per tour with role-based permissions (lead vs assistant)
- [ ] **Photo Gallery** (per tour) — guide uploads photos
  - Client-side image compression before upload (max 1200px, 80% JPEG via Pillow/JS)
  - Lightbox viewer; delete photo; photos organised by tour + optionally by activity
  - Bulk photo upload after tour
- [ ] Booking management: view RSVPs, confirm/cancel, manual tour code assignment
- [ ] Revenue overview: bookings, payments, per-tour summary (charts via Chart.js)
- [ ] Guide permissions toggle (superuser controls what guides can see — health data, contacts, financial, notes)
- [ ] Notification manager UI (see Phase 8)
- [ ] PDF export — guest manifest, itinerary, waiver records, post-tour summary
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

### Phase 12 — NFC + QR Scanner
Web NFC API for tour check-in and QR code join flow.

- [ ] **QR Scanner** — guest scans tour QR code to join (primary; works iOS + Android)
  - JS-based QR scanner in PWA (e.g., `jsQR` library); no native app required
  - Scan → tour code extracted → same join_lookup flow as text entry
- [ ] `apps/nfc/models.py` — `NFCTag` model (booking/activity link)
- [ ] Web NFC API write (guide writes tour join URL + tour code to NFC tag via dashboard)
- [ ] Web NFC API read (guest taps tag → instant enrollment, skipping camera/QR entirely)
- [ ] Activity check-in NFC tags (each waypoint tag encodes tour ID + item ID → confirms attendance)
- [ ] Medical wristbands — write guest name, emergency contact, allergies, blood type to NFC tag during onboarding; any first responder can tap to read
- [ ] QR code fallback for iOS (Web NFC is Android Chrome only — documented limitation)
- [ ] NFC tap simulation button in DEV_MODE

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

### Phase 16 — Weather Widget
OpenWeatherMap integration for guests during active tours.

- [ ] OpenWeatherMap One Call API 3.0 integration via Celery task (async fetch)
- [ ] `apps/tours/models.py` — `WeatherCache` model (location, data JSON, fetched_at, expires_at)
- [ ] Current conditions widget: temp, humidity, wind, weather description + icon
- [ ] 5-day forecast with daily breakdowns; date-specific forecast for upcoming activity days
- [ ] 30-minute cache via Celery to reduce API calls; stale cache fallback when offline
- [ ] Weather widget partial rendered via HTMX on itinerary page

### Phase 17 — Guest Experience Enhancements

- [ ] **Offline itinerary cache** — full offline access via service worker + IndexedDB fallback
- [ ] **Tour ratings & reviews** — post-tour feedback form (star rating + comments); visible in admin
- [ ] **Trip Memory Album** — guide + guest photos auto-collected into tour album view
- [ ] **Accessibility** — screen reader support, high-contrast mode, text-size adjustments
- [ ] **Offline indicator banner** — visual banner when network connectivity is lost
- [ ] **PWA install prompt** — custom "Add to Home Screen" prompt (BeforeInstallPrompt)
- [ ] **Auto-update banner** — prompt users when new service worker version available

### Phase 18 — Compliance + Data Management

- [ ] **Waiver versioning** — track template versions; prompt re-signing if terms change
- [ ] **POPIA/GDPR compliance** — data export (guest downloads own data), account deletion, consent management
- [ ] **Geo-fencing alerts** — guide notified via push if a guest leaves predefined safe zone (Celery + GPS)

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
| In-app chat | Django Channels WebSocket — replace WhatsApp group dependence |
| Real-time guest map | Guide sees all opted-in guest positions live during tour |
| Public tour marketplace | Discoverable listing of tours for direct-to-consumer bookings |
| Referral programme | Guest referral links for discounts on future tours |
| White-label mode | Per-operator branding (logo, colours, custom domain) |
| Group bookings | Single booking covering multiple guests |
| Live guide tracking | Real-time GPS share from guide to all guests during tour |
| SOS to emergency services | Direct dispatch integration beyond WhatsApp |

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
