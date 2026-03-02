# Phase 6 — PWA Core Screens Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build all PWA-facing templates matching the 15 UI reference screenshots (Tasks 15-20 from ROADMAP).

**Architecture:** Django views + HTMX (settings toggles) + Alpine.js (GPS share). All screens extend `base_app.html`. Home screen suppresses bottom nav via `{% block bottom_nav %}` override. Join confirmation suppresses nav too. Tour code join uses POST/redirect (not HTMX) for reliability.

**Tech Stack:** Django 6 · HTMX 2.0 · Alpine.js 3.14 · Bootstrap 5.3 · custom CSS in `static/css/app.css`

**Risk level:** 2 (standard features — views + templates). No adversarial review needed.

**Reference screenshots:** `plannig/UI/` — 1000220114 (home no-tours), 1000220122 (home with-tours), 1000220116 (join confirm), 1000220118-120 (itinerary), 1000220126 (map), 1000220128-130 (profile).

---

## Final URL Map

```
/                            → apps.landing  (home — no bottom nav)
/accounts/profile/           → apps.accounts (profile view — NEW)
/app/sos/                    → apps.sos      (SOS screen — NEW)
/app/map/                    → apps.maps     (map screen — NEW)
/app/itinerary/              → apps.bookings (most-recent booking redirect — NEW)
/app/itinerary/<id>/         → apps.bookings (itinerary detail — NEW)
/app/itinerary/<id>/rsvp/    → apps.bookings (RSVP action — NEW)
/app/join/                   → apps.bookings (tour code POST lookup — NEW)
/app/join/<code>/            → apps.bookings (join confirmation page — NEW)
```

## Key base_app.html changes

1. Wrap `<main>` class in `{% block main_class %}{% if user.is_authenticated %}page-with-nav{% endif %}{% endblock %}` so home can suppress padding.
2. Wrap bottom nav in `{% block bottom_nav %}{% if user.is_authenticated %}{% include ... %}{% endif %}{% endblock %}` so home/join can suppress it.
3. Add service worker `<script>` before `</body>`.

---

## Shared test helper

Paste into each test module that needs an authenticated user:

```python
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile

def _make_user(email='t@test.com'):
    User = get_user_model()
    u = User.objects.create_user(username=email, email=email, password='x', is_active=True)
    UserProfile.objects.filter(user=u).update(first_name='Gavin', indemnity_accepted=True)
    return u
```

---

## Task 15: PWA Assets + base_app.html blocks

**Files:**
- Create: `static/manifest.json`
- Create: `static/js/service-worker.js`
- Modify: `templates/base_app.html`
- Create: `apps/landing/tests/test_pwa.py`

**Step 1: Write failing test**

`apps/landing/tests/test_pwa.py`:
```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile

def _make_user():
    User = get_user_model()
    u = User.objects.create_user(username='t@t.com', email='t@t.com', password='x', is_active=True)
    UserProfile.objects.filter(user=u).update(first_name='T', indemnity_accepted=True)
    return u

class BaseTemplateTest(TestCase):
    def test_manifest_and_sw_in_base(self):
        # We verify the base template references both assets.
        # Once the home view is wired in Task 16 this test drives the full render.
        self.client.force_login(_make_user())
        # Home redirects to setup if first_name is short — patch to be safe
        resp = self.client.get('/accounts/profile/')
        # Profile page uses base_app.html; /accounts/profile/ not wired yet so 404 is fine
        # Just confirm base_app.html itself contains the references (template render test)
        from django.template.loader import render_to_string
        html = render_to_string('base_app.html', {'user': _make_user()}, request=None)
        self.assertIn('manifest.json', html)
        self.assertIn('service-worker.js', html)
```

**Step 2: Run — FAIL**
```
pytest apps/landing/tests/test_pwa.py -v
# FAIL: service-worker.js not in base_app.html yet
```

**Step 3: Create `static/manifest.json`**
```json
{
  "name": "Overstrand Adventures",
  "short_name": "OVA",
  "description": "Your Overstrand adventure companion",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#FAF5EE",
  "theme_color": "#F97316",
  "orientation": "portrait",
  "scope": "/",
  "icons": [
    {"src": "/static/img/logo.png", "sizes": "192x192", "type": "image/png"},
    {"src": "/static/img/logo.png", "sizes": "512x512", "type": "image/png"}
  ]
}
```

**Step 4: Create `static/js/service-worker.js`**
```javascript
const CACHE = 'ova-v1';
const PRECACHE = [
  '/static/css/app.css',
  '/static/manifest.json',
  '/static/img/logo.png',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
```

**Step 5: Modify `templates/base_app.html`**

Replace the `<main>` opening tag:
```html
  <main id="main-content" class="{% block main_class %}{% if user.is_authenticated %}page-with-nav{% endif %}{% endblock %}">
```

Replace `{% if user.is_authenticated %}{% include 'app/partials/bottom_nav.html' %}{% endif %}` with:
```html
  {% block bottom_nav %}
    {% if user.is_authenticated %}
      {% include 'app/partials/bottom_nav.html' %}
    {% endif %}
  {% endblock %}
```

Replace the closing `{% block extra_js %}{% endblock %}` with:
```html
  <script>
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/static/js/service-worker.js');
    }
  </script>
  {% block extra_js %}{% endblock %}
</body>
```

**Step 6: Run test — PASS**
```
pytest apps/landing/tests/test_pwa.py -v
# PASS: 1 passed
```

**Step 7: Commit**
```bash
git add static/manifest.json static/js/service-worker.js templates/base_app.html apps/landing/tests/test_pwa.py
git commit -m "feat: PWA manifest, service worker, base_app template nav/class blocks"
```

---

## Task 16: URL wiring + stub views

**Files:**
- Modify: `overberg_adventures/urls.py`
- Modify: `overberg_adventures/settings.py`
- Modify: `apps/landing/urls.py` + `views.py`
- Modify: `apps/bookings/urls.py` + `views.py`
- Modify: `apps/sos/urls.py` + `views.py`
- Modify: `apps/maps/urls.py` + `views.py`
- Modify: `apps/accounts/urls.py` + `views.py`
- Modify: `templates/app/partials/bottom_nav.html`

**Step 1: Write URL resolution test** — `apps/landing/tests/test_urls.py`:
```python
from django.test import TestCase
from django.urls import reverse

class URLsTest(TestCase):
    def test_home(self):          self.assertEqual(reverse('landing:home'), '/')
    def test_itinerary(self):     self.assertEqual(reverse('bookings:itinerary_home'), '/app/itinerary/')
    def test_sos(self):           self.assertEqual(reverse('sos:sos'), '/app/sos/')
    def test_map(self):           self.assertEqual(reverse('maps:map'), '/app/map/')
    def test_profile(self):       self.assertEqual(reverse('accounts:profile'), '/accounts/profile/')
    def test_join_lookup(self):   self.assertEqual(reverse('bookings:join_lookup'), '/app/join/')
    def test_join_confirm(self):
        self.assertEqual(reverse('bookings:join_confirm', args=['fynbos']), '/app/join/fynbos/')
```

**Step 2: Run — FAIL**
```
pytest apps/landing/tests/test_urls.py -v
```

**Step 3: Update `overberg_adventures/settings.py`**
Change `LOGIN_REDIRECT_URL = '/app/'` to `LOGIN_REDIRECT_URL = '/'`

**Step 4: Update `overberg_adventures/urls.py`**
```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('app/sos/', include('apps.sos.urls', namespace='sos')),
    path('app/map/', include('apps.maps.urls', namespace='maps')),
    path('app/', include('apps.bookings.urls', namespace='bookings')),
    path('', include('apps.landing.urls', namespace='landing')),
    path('webpush/', include('webpush.urls')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**Step 5: Update `apps/landing/urls.py`**
```python
from django.urls import path
from . import views

app_name = 'landing'
urlpatterns = [
    path('', views.home, name='home'),
]
```

**Step 6: Update `apps/bookings/urls.py`**
```python
from django.urls import path
from . import views

app_name = 'bookings'
urlpatterns = [
    path('itinerary/', views.itinerary_home, name='itinerary_home'),
    path('itinerary/<int:booking_id>/', views.itinerary_detail, name='itinerary_detail'),
    path('itinerary/<int:booking_id>/rsvp/', views.rsvp_action, name='rsvp_action'),
    path('join/', views.join_lookup, name='join_lookup'),
    path('join/<str:tour_code>/', views.join_confirm, name='join_confirm'),
]
```

**Step 7: Update `apps/sos/urls.py`**
```python
from django.urls import path
from . import views

app_name = 'sos'
urlpatterns = [path('', views.sos_screen, name='sos')]
```

**Step 8: Update `apps/maps/urls.py`**
```python
from django.urls import path
from . import views

app_name = 'maps'
urlpatterns = [path('', views.map_screen, name='map')]
```

**Step 9: Add profile URL to `apps/accounts/urls.py`** — append to urlpatterns:
```python
path('profile/', views.profile_view, name='profile'),
```

**Step 10: Add stub implementations**

`apps/landing/views.py`:
```python
from django.shortcuts import render, redirect
from apps.bookings.models import Booking

def home(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    if not request.user.profile.setup_complete:
        return redirect('accounts:profile_setup')
    bookings = (
        Booking.objects.filter(user=request.user)
        .exclude(status=Booking.Status.CANCELLED)
        .select_related('tour')
        .order_by('-tour__start_datetime')
    )
    return render(request, 'app/home.html', {'bookings': bookings})
```

`apps/bookings/views.py` (full stub — will be fleshed out in Tasks 18-19):
```python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from apps.tours.models import Tour
from .models import Booking

@login_required
def itinerary_home(request):
    booking = (
        Booking.objects.filter(user=request.user)
        .exclude(status=Booking.Status.CANCELLED)
        .select_related('tour').order_by('-tour__start_datetime').first()
    )
    if booking:
        return redirect('bookings:itinerary_detail', booking_id=booking.id)
    return render(request, 'app/itinerary_empty.html', {})

@login_required
def itinerary_detail(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related('tour', 'tour__guide', 'tour__guide__profile'),
        pk=booking_id, user=request.user,
    )
    items_by_day = {}
    for item in booking.tour.itinerary_items.select_related('category').all():
        items_by_day.setdefault(item.day, []).append(item)
    return render(request, 'app/itinerary.html', {
        'booking': booking,
        'tour': booking.tour,
        'items_by_day': items_by_day,
    })

@login_required
@require_http_methods(['POST'])
def rsvp_action(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id, user=request.user)
    if booking.status == Booking.Status.INVITED:
        booking.status = Booking.Status.RSVP_PENDING
        booking.save(update_fields=['status'])
    return redirect('bookings:itinerary_detail', booking_id=booking_id)

@login_required
@require_http_methods(['POST'])
def join_lookup(request):
    code = request.POST.get('tour_code', '').strip().lower()
    try:
        tour = Tour.objects.get(tour_code=code, status=Tour.Status.ACTIVE)
    except Tour.DoesNotExist:
        messages.error(request, f'Tour code "{code.upper()}" not found.')
        return redirect('landing:home')
    existing = Booking.objects.filter(user=request.user, tour=tour).first()
    if existing:
        return redirect('bookings:itinerary_detail', booking_id=existing.id)
    return redirect('bookings:join_confirm', tour_code=code)

@login_required
@require_http_methods(['GET', 'POST'])
def join_confirm(request, tour_code):
    tour = get_object_or_404(Tour, tour_code=tour_code, status=Tour.Status.ACTIVE)
    existing = Booking.objects.filter(user=request.user, tour=tour).first()
    if existing:
        return redirect('bookings:itinerary_detail', booking_id=existing.id)
    if request.method == 'POST':
        try:
            booking = Booking.objects.create_from_rsvp(request.user, tour)
        except ValueError:
            messages.error(request, 'Sorry, this tour is now full.')
            return redirect('landing:home')
        return redirect('bookings:itinerary_detail', booking_id=booking.id)
    return render(request, 'app/join_confirm.html', {
        'tour': tour, 'profile': request.user.profile,
    })
```

`apps/sos/views.py`:
```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def sos_screen(request):
    return render(request, 'app/sos.html', {})
```

`apps/maps/views.py`:
```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def map_screen(request):
    return render(request, 'app/map.html', {})
```

Add to `apps/accounts/views.py` (after existing imports, at bottom of file):
```python
@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {
        'profile': request.user.profile,
        'dev_mode': getattr(settings, 'DEV_MODE', False),
    })
```

**Step 11: Create minimal stub templates** — each just extends base_app.html with a "stub" content block:
- `templates/app/home.html` → `{% extends 'base_app.html' %}{% block content %}home stub{% endblock %}`
- `templates/app/itinerary.html` → same pattern
- `templates/app/itinerary_empty.html` → same pattern
- `templates/app/join_confirm.html` → same pattern
- `templates/app/sos.html` → same pattern
- `templates/app/map.html` → same pattern
- `templates/accounts/profile.html` → same pattern

**Step 12: Update `templates/app/partials/bottom_nav.html`** — change profile link:
```html
<a href="{% url 'accounts:profile' %}" class="bottom-nav-item {% if request.path == '/accounts/profile/' %}active{% endif %}">
```
(Replace the existing `/accounts/setup/` href.)

**Step 13: Run URL tests — PASS**
```
pytest apps/landing/tests/test_urls.py -v
# Expected: 7 passed
```

**Step 14: Commit**
```bash
git add overberg_adventures/ apps/landing/ apps/bookings/ apps/sos/ apps/maps/ apps/accounts/ templates/
git commit -m "feat: wire all PWA routes — itinerary, join, sos, map, profile"
```

---

## Task 17: Home screen

**Files:**
- Modify: `templates/app/home.html` (replace stub)
- Create: `templates/app/partials/tour_card.html`
- Modify: `static/css/app.css`
- Modify: `apps/landing/tests/test_views.py`

**Step 1: Write tests** — `apps/landing/tests/test_views.py`:
```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.accounts.models import UserProfile
from apps.tours.models import Tour, TourCodeWord
from apps.bookings.models import Booking

def _make_user(email='g@g.com'):
    User = get_user_model()
    u = User.objects.create_user(username=email, email=email, password='x', is_active=True)
    UserProfile.objects.filter(user=u).update(first_name='Gavin', indemnity_accepted=True)
    return u

class HomeViewTest(TestCase):
    def test_redirects_unauthenticated(self):
        self.assertRedirects(self.client.get('/'), '/accounts/login/')

    def test_redirects_incomplete_setup(self):
        User = get_user_model()
        u = User.objects.create_user(username='x@x.com', email='x@x.com', password='x', is_active=True)
        self.client.force_login(u)
        resp = self.client.get('/')
        self.assertRedirects(resp, '/accounts/setup/')

    def test_shows_welcome_no_tours(self):
        self.client.force_login(_make_user())
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Welcome, Gavin')
        self.assertContains(resp, "You haven't joined any tours yet")

    def test_shows_my_tours(self):
        user = _make_user()
        TourCodeWord.objects.create(word='fynbos', is_used=True)
        tour = Tour.objects.create(
            name='Kogelberg Trek', tour_code='fynbos',
            start_datetime=timezone.now(), location_name='Kleinmond',
            capacity=10, status=Tour.Status.ACTIVE,
        )
        Booking.objects.create(user=user, tour=tour, status=Booking.Status.CONFIRMED)
        self.client.force_login(user)
        resp = self.client.get('/')
        self.assertContains(resp, 'MY TOURS')
        self.assertContains(resp, 'Kogelberg Trek')
```

**Step 2: Run — FAIL** (home stub doesn't contain "Welcome")

**Step 3: Implement `templates/app/home.html`**
```html
{% extends 'base_app.html' %}
{% load static %}
{% block title %}Home — Overstrand Adventures{% endblock %}
{% block main_class %}{% endblock %}
{% block bottom_nav %}{% endblock %}

{% block content %}
{% if messages %}
<div class="px-3 pt-3">
  {% for msg in messages %}
  <div class="alert alert-{{ msg.tags }} alert-dismissible" role="alert">
    {{ msg }}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  </div>
  {% endfor %}
</div>
{% endif %}

<div class="home-page">
  <div class="px-4 pt-4 pb-2 d-flex justify-content-end">
    <a href="{% url 'accounts:logout' %}" class="text-muted small">
      <i class="bi bi-box-arrow-right me-1"></i>Log Out
    </a>
  </div>

  <div class="home-hero text-center px-4 pb-4">
    <img src="{% static 'img/logo.png' %}" alt="Overstrand Adventures" class="home-logo mb-4">
    <h1 class="fw-bold mb-1">Welcome, {{ request.user.profile.first_name }}!</h1>
    <p class="text-muted">Enter your code to unlock the Overstrand</p>
  </div>

  <div class="px-4 mb-4">
    <div class="card-oa p-2">
      <form method="post" action="{% url 'bookings:join_lookup' %}" class="d-flex gap-2">
        {% csrf_token %}
        <input type="text" name="tour_code"
               placeholder="ENTER TOUR CODE"
               class="form-control-oa flex-grow-1 text-uppercase"
               style="letter-spacing:0.08em"
               autocomplete="off" autocapitalize="characters" required>
        <button type="submit" class="btn-oa-discover">Discover</button>
      </form>
    </div>
  </div>

  {% if bookings %}
  <div class="px-4">
    <h2 class="section-heading mb-3">
      <i class="bi bi-briefcase text-primary me-2"></i>MY TOURS
    </h2>
    {% for booking in bookings %}
      {% include 'app/partials/tour_card.html' with booking=booking %}
    {% endfor %}
  </div>
  {% else %}
  <div class="text-center text-muted px-4 mt-2">
    <p class="mb-1">You haven't joined any tours yet.</p>
    <p>Enter a tour code above to get started!</p>
  </div>
  {% endif %}

  <footer class="text-center text-muted small py-4 mt-auto">
    &copy; 2026 Overstrand Adventures &bull; All rights reserved
  </footer>
</div>
{% endblock %}
```

**Step 4: Create `templates/app/partials/tour_card.html`**
```html
<a href="{% url 'bookings:itinerary_detail' booking.id %}" class="tour-card d-block mb-3 text-decoration-none">
  <div class="d-flex justify-content-between align-items-start">
    <div>
      <h3 class="tour-card-name mb-1">{{ booking.tour.name }}</h3>
      <span class="tour-code-badge">{{ booking.tour.tour_code|upper }}</span>
      <span class="text-muted small ms-2">
        <i class="bi bi-calendar3 me-1"></i>{{ booking.tour.start_datetime|date:"H:i, l, j F" }}
      </span>
    </div>
    <div class="d-flex flex-column align-items-end gap-1">
      <span class="status-badge status-{{ booking.status|lower }}">{{ booking.get_status_display }}</span>
      <i class="bi bi-chevron-right text-muted mt-1"></i>
    </div>
  </div>
</a>
```

**Step 5: Add to `static/css/app.css`**
```css
/* ---- Home screen ---- */
.home-page { min-height: 100vh; display: flex; flex-direction: column; background: var(--color-bg); }
.home-logo { width: 200px; height: 200px; object-fit: contain; }

.btn-oa-discover {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  border: none; border-radius: 12px; color: white;
  font-weight: 700; padding: 14px 20px; white-space: nowrap; flex-shrink: 0;
}

.section-heading {
  font-size: 13px; font-weight: 700;
  letter-spacing: 0.08em; color: var(--color-text-muted); text-transform: uppercase;
}

/* ---- Tour card ---- */
.tour-card {
  background: var(--color-surface); border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06); padding: 16px; color: var(--color-text);
}
.tour-card-name { font-size: 17px; font-weight: 700; color: var(--color-text); }
.tour-code-badge { font-size: 11px; font-weight: 700; letter-spacing: 0.1em; color: var(--color-primary); }

/* ---- Status badges ---- */
.status-badge {
  font-size: 11px; font-weight: 600; padding: 3px 10px;
  border-radius: 20px; letter-spacing: 0.04em; text-transform: uppercase;
}
.status-confirmed    { background: #D1FAE5; color: #065F46; }
.status-rsvp_pending { background: #FEF3C7; color: #92400E; border: 1.5px solid #F59E0B; }
.status-invited      { background: #EDE9FE; color: #5B21B6; }
.status-completed    { background: #E5E7EB; color: #374151; }
.status-cancelled    { background: #FEE2E2; color: #991B1B; }
.status-active       { background: #D1FAE5; color: #065F46; }
.status-draft        { background: #F3F4F6; color: #6B7280; }
```

**Step 6: Run — PASS**
```
pytest apps/landing/tests/test_views.py -v
# Expected: 4 passed
```

**Step 7: Commit**
```bash
git add templates/app/home.html templates/app/partials/tour_card.html static/css/app.css apps/landing/tests/
git commit -m "feat: home screen — welcome, tour code form, my tours list"
```

---

## Task 18: Tour code join flow

**Files:**
- `apps/bookings/views.py` already implemented in Task 16; verify tests pass
- Modify: `templates/app/join_confirm.html` (replace stub)
- Create: `apps/bookings/tests/test_join.py`
- Add CSS to `static/css/app.css`

**Step 1: Write tests** — `apps/bookings/tests/test_join.py`:
```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.accounts.models import UserProfile
from apps.tours.models import Tour, TourCodeWord
from apps.bookings.models import Booking

def _make_user(email='g@g.com'):
    User = get_user_model()
    u = User.objects.create_user(username=email, email=email, password='x', is_active=True)
    UserProfile.objects.filter(user=u).update(first_name='Gavin', last_name='Holder', indemnity_accepted=True)
    return u

def _make_tour(code='fynbos'):
    TourCodeWord.objects.get_or_create(word=code, defaults={'is_used': True})
    return Tour.objects.create(
        name='Overstrand Unlocked', tour_code=code,
        start_datetime=timezone.now(), location_name='Kleinmond',
        capacity=10, status=Tour.Status.ACTIVE,
    )

class JoinLookupTest(TestCase):
    def test_redirects_unauthenticated(self):
        resp = self.client.post('/app/join/', {'tour_code': 'fynbos'})
        self.assertIn('/accounts/login/', resp['Location'])

    def test_valid_code_redirects_to_confirm(self):
        _make_tour('fynbos')
        self.client.force_login(_make_user())
        resp = self.client.post('/app/join/', {'tour_code': 'FYNBOS'})  # test case-insensitive
        self.assertRedirects(resp, '/app/join/fynbos/')

    def test_invalid_code_redirects_home(self):
        self.client.force_login(_make_user())
        resp = self.client.post('/app/join/', {'tour_code': 'unknown'})
        self.assertRedirects(resp, '/')

    def test_already_booked_redirects_to_itinerary(self):
        user = _make_user()
        tour = _make_tour('pelican')
        booking = Booking.objects.create(user=user, tour=tour, status=Booking.Status.CONFIRMED)
        self.client.force_login(user)
        resp = self.client.post('/app/join/', {'tour_code': 'pelican'})
        self.assertRedirects(resp, f'/app/itinerary/{booking.id}/')

class JoinConfirmTest(TestCase):
    def test_confirm_page_shows_tour_info(self):
        _make_tour('milkwood')
        self.client.force_login(_make_user())
        resp = self.client.get('/app/join/milkwood/')
        self.assertContains(resp, 'Overstrand Unlocked')
        self.assertContains(resp, 'Kleinmond')

    def test_confirm_page_shows_user_info(self):
        _make_tour('whale')
        self.client.force_login(_make_user())
        resp = self.client.get('/app/join/whale/')
        self.assertContains(resp, 'Gavin Holder')

    def test_post_creates_booking_and_redirects(self):
        tour = _make_tour('kogelberg')
        user = _make_user()
        self.client.force_login(user)
        resp = self.client.post('/app/join/kogelberg/')
        booking = Booking.objects.get(user=user, tour=tour)
        self.assertRedirects(resp, f'/app/itinerary/{booking.id}/')

    def test_full_tour_redirects_home(self):
        tour = _make_tour('whale2')
        tour.capacity = 1
        tour.save()
        other = _make_user('other@test.com')
        Booking.objects.create(user=other, tour=tour, status=Booking.Status.CONFIRMED)
        self.client.force_login(_make_user('me@test.com'))
        resp = self.client.post('/app/join/whale2/')
        self.assertRedirects(resp, '/')
```

**Step 2: Run — some FAIL** (template stub returns 200 but without "Kleinmond")
```
pytest apps/bookings/tests/test_join.py -v
```

**Step 3: Implement `templates/app/join_confirm.html`**
```html
{% extends 'base_app.html' %}
{% block title %}Join {{ tour.name }}{% endblock %}
{% block main_class %}{% endblock %}
{% block bottom_nav %}{% endblock %}

{% block content %}
<div class="join-page px-4 py-5">

  <div class="join-header-card mb-3">
    <h1 class="fw-bold text-white mb-2">{{ tour.name }}</h1>
    <p class="mb-0 small" style="color:rgba(255,255,255,0.85)">
      <i class="bi bi-calendar3 me-1"></i>{{ tour.start_datetime|date:"j M, Y" }}
      <span class="ms-3"><i class="bi bi-geo-alt me-1"></i>{{ tour.location_name }}</span>
    </p>
  </div>

  <div class="card-oa mb-4">
    <div class="d-flex align-items-center gap-3 mb-3">
      <div class="avatar-md bg-purple d-flex align-items-center justify-content-center text-white fw-bold"
           style="font-size:1.2rem">
        {{ profile.initials|upper }}
      </div>
      <div>
        <div class="fw-bold">{{ profile.full_name }}</div>
        <div class="text-muted small">{{ request.user.email }}</div>
      </div>
    </div>
    <p class="text-muted small mb-0">
      You're about to join this trip. Your profile information will be shared with the guide.
    </p>
  </div>

  <form method="post">
    {% csrf_token %}
    <button type="submit" class="btn-oa-primary mb-3">
      <i class="bi bi-check2 me-2"></i>Join This Trip
    </button>
  </form>
  <a href="/" class="d-block text-center text-muted">Cancel</a>
</div>
{% endblock %}
```

**Step 4: Add CSS to `static/css/app.css`**
```css
/* ---- Join confirm ---- */
.join-page { min-height: 100vh; }
.join-header-card {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  border-radius: 16px; padding: 24px 20px;
}
.avatar-md { width: 52px; height: 52px; border-radius: 50%; flex-shrink: 0; }
```

**Step 5: Run — PASS**
```
pytest apps/bookings/tests/test_join.py -v
# Expected: 8 passed
```

**Step 6: Commit**
```bash
git add apps/bookings/tests/ templates/app/join_confirm.html static/css/app.css
git commit -m "feat: tour code join flow — lookup, confirmation page, booking creation"
```

---

## Task 19: Itinerary screen

**Files:**
- Modify: `templates/app/itinerary.html` (replace stub)
- Modify: `templates/app/itinerary_empty.html` (replace stub)
- Create: `templates/app/partials/activity_card.html`
- Modify: `static/css/app.css`
- Create: `apps/bookings/tests/test_itinerary.py`

**Step 1: Write tests** — `apps/bookings/tests/test_itinerary.py`:
```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.accounts.models import UserProfile
from apps.tours.models import Tour, TourCodeWord, ItineraryItem, ActivityCategory
from apps.bookings.models import Booking

def _setup(email='g@g.com'):
    User = get_user_model()
    user = User.objects.create_user(username=email, email=email, password='x', is_active=True)
    UserProfile.objects.filter(user=user).update(first_name='Gavin', indemnity_accepted=True)
    TourCodeWord.objects.get_or_create(word='fynbos', defaults={'is_used': True})
    tour = Tour.objects.create(
        name='Kogelberg Trek', tour_code='fynbos',
        start_datetime=timezone.now(), location_name='Kleinmond',
        capacity=10, status=Tour.Status.ACTIVE,
    )
    cat = ActivityCategory.objects.create(name='Hiking', icon='mountains', colour='#F97316')
    ItineraryItem.objects.create(
        tour=tour, day=1, order=1, title='Palmiet River Walk',
        start_time='08:45', duration_minutes=120,
        category=cat, difficulty='MODERATE', distance_km='10',
    )
    booking = Booking.objects.create(user=user, tour=tour, status=Booking.Status.CONFIRMED)
    return user, tour, booking

class ItineraryDetailTest(TestCase):
    def test_redirects_unauthenticated(self):
        resp = self.client.get('/app/itinerary/999/')
        self.assertIn('/accounts/login/', resp['Location'])

    def test_404_for_wrong_user(self):
        user, tour, booking = _setup()
        User = get_user_model()
        other = User.objects.create_user(username='o@o.com', email='o@o.com', password='x', is_active=True)
        self.client.force_login(other)
        self.assertEqual(self.client.get(f'/app/itinerary/{booking.id}/').status_code, 404)

    def test_shows_tour_and_activity(self):
        user, tour, booking = _setup()
        self.client.force_login(user)
        resp = self.client.get(f'/app/itinerary/{booking.id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Kogelberg Trek')
        self.assertContains(resp, 'Palmiet River Walk')
        self.assertContains(resp, 'Kleinmond')

    def test_itinerary_home_redirects_to_active_booking(self):
        user, tour, booking = _setup('h@h.com')
        self.client.force_login(user)
        resp = self.client.get('/app/itinerary/')
        self.assertRedirects(resp, f'/app/itinerary/{booking.id}/')
```

**Step 2: Run — some FAIL** (stubs don't contain tour content)

**Step 3: Implement `templates/app/itinerary.html`**
```html
{% extends 'base_app.html' %}
{% load static %}
{% block title %}{{ tour.name }}{% endblock %}

{% block content %}
<div class="map-banner">
  <div class="map-banner-placeholder d-flex align-items-center justify-content-center">
    <span class="text-muted small">Map — Phase 7</span>
  </div>
</div>

{% if booking.status == 'INVITED' or booking.status == 'RSVP_PENDING' %}
<div class="card-oa mx-3 mt-3">
  <div class="d-flex align-items-center gap-2 mb-2">
    <span style="font-size:1.3rem">&#x1F44B;</span>
    <strong>You're Invited!</strong>
  </div>
  <p class="text-muted small mb-2">Please confirm your attendance to secure your spot.</p>
  {% if tour.spots_remaining <= 10 %}
  <p class="small mb-2 fw-semibold" style="color:var(--color-primary)">
    Hurry, there are only {{ tour.spots_remaining }} spots left.
  </p>
  {% endif %}
  {% if booking.status == 'INVITED' %}
  <form method="post" action="{% url 'bookings:rsvp_action' booking.id %}">
    {% csrf_token %}
    <button type="submit" class="btn-oa-primary" style="padding:10px">RSVP Now</button>
  </form>
  {% endif %}
</div>
{% endif %}

<div class="px-3 pt-3 pb-4">
  <div class="d-flex justify-content-between align-items-start mb-1">
    <h1 class="fw-bold mb-0" style="font-size:1.35rem">{{ tour.name }}</h1>
    <span class="status-badge status-{{ booking.status|lower }}">{{ booking.get_status_display }}</span>
  </div>
  <p class="text-muted small mb-3 fw-semibold" style="letter-spacing:0.06em">
    {{ tour.itinerary_items.count }} ACTIVIT{{ tour.itinerary_items.count|pluralize:"Y,IES" }}
  </p>

  <div class="itinerary-meta mb-4">
    <div class="itinerary-meta-row">
      <span class="meta-label">Start</span>
      <span class="meta-value"><i class="bi bi-calendar3 me-1"></i>{{ tour.start_datetime|date:"H:i, l, j F" }}</span>
      <span class="status-badge status-{{ tour.status|lower }} ms-auto">{{ tour.get_status_display }}</span>
    </div>
    <div class="itinerary-meta-row">
      <span class="meta-label">Location</span>
      <span class="meta-value"><i class="bi bi-geo-alt me-1"></i>{{ tour.location_name }}</span>
      {% if tour.location_lat and tour.location_lng %}
      <a href="https://maps.google.com/?q={{ tour.location_lat }},{{ tour.location_lng }}"
         target="_blank" rel="noopener" class="meta-action-btn text-primary ms-auto">
        <i class="bi bi-arrow-up-right-square me-1"></i>Directions
      </a>
      {% endif %}
    </div>
    {% if tour.guide %}
    <div class="itinerary-meta-row">
      <span class="meta-label">Guide</span>
      <span class="meta-value"><i class="bi bi-person me-1"></i>{{ tour.guide.profile.full_name }}</span>
      {% if tour.guide.profile.phone_whatsapp %}
      <a href="https://wa.me/{{ tour.guide.profile.phone_whatsapp }}"
         target="_blank" rel="noopener" class="meta-action-btn text-success ms-auto">
        <i class="bi bi-chat me-1"></i>Contact
      </a>
      {% endif %}
    </div>
    {% endif %}
  </div>

  {% for day, activities in items_by_day.items %}
  <div class="mb-4">
    <div class="day-header mb-3">
      <i class="bi bi-chevron-down me-2 text-muted"></i>
      <span class="fw-bold text-muted small" style="letter-spacing:0.08em">DAY {{ day }}</span>
    </div>
    <div class="activity-timeline">
      {% for item in activities %}
        {% include 'app/partials/activity_card.html' with item=item is_last=forloop.last %}
      {% endfor %}
    </div>
  </div>
  {% endfor %}
</div>
{% endblock %}
```

**Step 4: Implement `templates/app/itinerary_empty.html`**
```html
{% extends 'base_app.html' %}
{% block title %}Itinerary{% endblock %}
{% block content %}
<div class="text-center py-5 px-4">
  <i class="bi bi-map" style="font-size:3rem;color:var(--color-border)"></i>
  <h2 class="mt-3 mb-2">No tours yet</h2>
  <p class="text-muted">Enter a tour code on the home screen to get started.</p>
  <a href="/" class="btn-oa-primary mt-2 d-inline-block" style="width:auto;padding:12px 32px">Go Home</a>
</div>
{% endblock %}
```

**Step 5: Create `templates/app/partials/activity_card.html`**
```html
<div class="activity-row mb-3">
  <div class="activity-icon-col">
    <div class="category-circle"
         style="background:{{ item.category.colour|default:'#9CA3AF' }}20;border:2px solid {{ item.category.colour|default:'#9CA3AF' }}">
      <i class="bi bi-{{ item.category.icon|default:'compass' }}"
         style="color:{{ item.category.colour|default:'#9CA3AF' }};font-size:1rem"></i>
    </div>
    {% if not is_last %}<div class="timeline-connector"></div>{% endif %}
  </div>
  <div class="card-oa ms-3 flex-grow-1" style="padding:14px">
    <div class="d-flex justify-content-between align-items-start mb-1">
      <h4 class="activity-title mb-0">{{ item.title }}</h4>
      <span class="time-badge ms-2"><i class="bi bi-clock me-1"></i>{{ item.start_time|time:"H:i" }}</span>
    </div>
    {% if item.location_name %}
    <p class="text-muted small mb-1"><i class="bi bi-geo-alt me-1"></i>{{ item.location_name }}</p>
    {% endif %}
    <div class="d-flex align-items-center gap-2 flex-wrap mt-1">
      <span class="text-muted small">{{ item.get_difficulty_display }}</span>
      <span class="text-muted small">&middot;</span>
      <span class="text-muted small"><i class="bi bi-clock me-1"></i>{{ item.duration_display }}</span>
      {% if item.distance_km %}
      <span class="text-muted small">&middot;</span>
      <span class="text-muted small">{{ item.distance_km }} km</span>
      {% endif %}
      {% if item.category %}
      <span class="category-badge ms-auto"
            style="border-color:{{ item.category.colour }};color:{{ item.category.colour }}">
        {{ item.category.name|upper }}
      </span>
      {% endif %}
    </div>
  </div>
</div>
```

**Step 6: Add CSS to `static/css/app.css`**
```css
/* ---- Itinerary ---- */
.map-banner { height: 220px; }
.map-banner-placeholder {
  height: 100%;
  background: linear-gradient(180deg, #2d4a2d 0%, #1a3a2a 100%);
}
.itinerary-meta { display: flex; flex-direction: column; gap: 10px; }
.itinerary-meta-row { display: flex; align-items: center; gap: 8px; font-size: 14px; }
.meta-label { color: var(--color-text-muted); min-width: 64px; }
.meta-action-btn {
  font-size: 13px; font-weight: 600; text-decoration: none;
  border: 1.5px solid currentColor; border-radius: 20px; padding: 3px 10px;
}
.day-header { display: flex; align-items: center; }
.activity-timeline { display: flex; flex-direction: column; }
.activity-row { display: flex; align-items: flex-start; }
.activity-icon-col { display: flex; flex-direction: column; align-items: center; flex-shrink: 0; }
.category-circle {
  width: 44px; height: 44px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.timeline-connector {
  width: 2px; flex-grow: 1; min-height: 16px;
  background: var(--color-border); margin: 4px 0;
}
.activity-title { font-size: 16px; font-weight: 700; }
.time-badge {
  font-size: 12px; font-weight: 600; color: var(--color-primary);
  border: 1.5px solid var(--color-primary); border-radius: 20px;
  padding: 2px 8px; white-space: nowrap;
}
.category-badge {
  font-size: 11px; font-weight: 700; letter-spacing: 0.06em;
  border: 1.5px solid; border-radius: 20px; padding: 2px 8px;
}
```

**Step 7: Run — PASS**
```
pytest apps/bookings/tests/test_itinerary.py -v
# Expected: 4 passed
```

**Step 8: Commit**
```bash
git add apps/bookings/tests/ templates/app/itinerary.html templates/app/itinerary_empty.html templates/app/partials/activity_card.html static/css/app.css
git commit -m "feat: itinerary screen — map banner, RSVP, day sections, activity timeline cards"
```

---

## Task 20: SOS screen

**Files:**
- Modify: `apps/sos/models.py`
- Create: migration
- Modify: `apps/sos/views.py`
- Modify: `templates/app/sos.html`
- Modify: `static/css/app.css`
- Create: `apps/sos/tests/test_sos.py`

**Step 1: Write tests** — `apps/sos/tests/test_sos.py`:
```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile
from apps.sos.models import SosConfig, EmergencyContact

def _make_user():
    User = get_user_model()
    u = User.objects.create_user(username='s@s.com', email='s@s.com', password='x', is_active=True)
    UserProfile.objects.filter(user=u).update(first_name='S', indemnity_accepted=True)
    return u

class SOSViewTest(TestCase):
    def test_redirects_unauthenticated(self):
        self.assertIn('/accounts/login/', self.client.get('/app/sos/')['Location'])

    def test_sos_screen_loads(self):
        self.client.force_login(_make_user())
        self.assertEqual(self.client.get('/app/sos/').status_code, 200)

    def test_shows_emergency_number(self):
        SosConfig.objects.create(emergency_number='10111')
        self.client.force_login(_make_user())
        self.assertContains(self.client.get('/app/sos/'), '10111')

    def test_shows_emergency_contacts(self):
        EmergencyContact.objects.create(name='Mountain Rescue', phone='+27219876543', role='SAR')
        self.client.force_login(_make_user())
        self.assertContains(self.client.get('/app/sos/'), 'Mountain Rescue')
```

**Step 2: Run — FAIL**

**Step 3: Implement `apps/sos/models.py`**
```python
from django.db import models

class SosConfig(models.Model):
    emergency_number = models.CharField(max_length=20, default='112')
    show_emergency_call = models.BooleanField(default=True)
    show_gps_share = models.BooleanField(default=True)
    show_emergency_contacts = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'SOS Configuration'

    def __str__(self):
        return 'SOS Configuration'

class EmergencyContact(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    role = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name
```

**Step 4: Make and run migration**
```
python manage.py makemigrations sos
python manage.py migrate
```

**Step 5: Register in `apps/sos/admin.py`**
```python
from django.contrib import admin
from .models import SosConfig, EmergencyContact

admin.site.register(SosConfig)
admin.site.register(EmergencyContact)
```

**Step 6: Implement `apps/sos/views.py`**
```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import SosConfig, EmergencyContact

@login_required
def sos_screen(request):
    config = SosConfig.objects.first() or SosConfig()
    contacts = EmergencyContact.objects.filter(is_active=True) if config.show_emergency_contacts else []
    return render(request, 'app/sos.html', {'config': config, 'contacts': contacts})
```

**Step 7: Implement `templates/app/sos.html`**
```html
{% extends 'base_app.html' %}
{% block title %}SOS — Emergency{% endblock %}

{% block content %}
<div class="px-4 pt-4 pb-4">
  <h1 class="fw-bold mb-1">SOS</h1>
  <p class="text-muted small mb-4">Emergency assistance options</p>

  {% if config.show_emergency_call %}
  <div class="card-oa mb-3 text-center">
    <h2 class="fw-bold mb-2" style="font-size:1.1rem">Emergency Call</h2>
    <a href="tel:{{ config.emergency_number }}" class="sos-emergency-btn">
      <i class="bi bi-telephone-fill me-2"></i>Call {{ config.emergency_number }}
    </a>
  </div>
  {% endif %}

  {% if config.show_gps_share %}
  <div class="card-oa mb-3" x-data="gpsShare()">
    <h2 class="fw-bold mb-2" style="font-size:1.1rem">
      <i class="bi bi-geo-alt-fill text-primary me-2"></i>Share My Location
    </h2>
    <button x-on:click="share()" class="btn-oa-outline w-100" x-bind:disabled="loading">
      <i class="bi bi-share me-2"></i>
      <span x-text="loading ? 'Getting location...' : 'Share GPS Link'">Share GPS Link</span>
    </button>
    <p x-show="error" x-cloak class="text-danger small mt-2" x-text="error"></p>
    <p x-show="link" x-cloak class="small mt-2">
      Link: <a x-bind:href="link" target="_blank" rel="noopener" x-text="link"></a>
    </p>
  </div>
  {% endif %}

  {% if config.show_emergency_contacts and contacts %}
  <div class="card-oa">
    <h2 class="fw-bold mb-3" style="font-size:1.1rem">
      <i class="bi bi-people-fill text-primary me-2"></i>Emergency Contacts
    </h2>
    {% for contact in contacts %}
    <div class="d-flex justify-content-between align-items-center {% if not forloop.last %}mb-3 pb-3 border-bottom{% endif %}">
      <div>
        <div class="fw-semibold">{{ contact.name }}</div>
        {% if contact.role %}<div class="text-muted small">{{ contact.role }}</div>{% endif %}
      </div>
      <a href="tel:{{ contact.phone }}" class="sos-contact-btn">
        <i class="bi bi-telephone-fill"></i>
      </a>
    </div>
    {% endfor %}
  </div>
  {% endif %}
</div>
{% endblock %}

{% block extra_js %}
<script>
function gpsShare() {
  return {
    loading: false, error: '', link: '',
    share() {
      this.error = ''; this.link = ''; this.loading = true;
      navigator.geolocation.getCurrentPosition(
        pos => {
          this.loading = false;
          const lat = pos.coords.latitude.toFixed(6);
          const lng = pos.coords.longitude.toFixed(6);
          this.link = 'https://maps.google.com/?q=' + lat + ',' + lng;
        },
        () => {
          this.loading = false;
          this.error = 'Could not get location. Please check app permissions.';
        }
      );
    }
  };
}
</script>
{% endblock %}
```

**Step 8: Add CSS**
```css
/* ---- SOS screen ---- */
.sos-emergency-btn {
  background: #EF4444; color: white; border: none; border-radius: 14px;
  padding: 18px; font-size: 1.1rem; font-weight: 700; text-decoration: none; display: block;
}
.sos-contact-btn {
  background: var(--color-primary); color: white; border-radius: 50%;
  width: 40px; height: 40px; display: flex; align-items: center;
  justify-content: center; text-decoration: none; flex-shrink: 0;
}
```

**Step 9: Run — PASS**
```
pytest apps/sos/tests/ -v
# Expected: 4 passed
```

**Step 10: Commit**
```bash
git add apps/sos/ templates/app/sos.html static/css/app.css
git commit -m "feat: SOS screen — emergency call, GPS share (Alpine.js), contacts model + admin"
```

---

## Task 21: Map screen stub

**Files:**
- Modify: `apps/maps/views.py`
- Modify: `templates/app/map.html`
- Modify: `static/css/app.css`
- Create: `apps/maps/tests/test_map.py`

**Step 1: Write tests** — `apps/maps/tests/test_map.py`:
```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile

class MapViewTest(TestCase):
    def test_redirects_unauthenticated(self):
        self.assertIn('/accounts/login/', self.client.get('/app/map/')['Location'])

    def test_map_screen_loads(self):
        User = get_user_model()
        u = User.objects.create_user(username='m@m.com', email='m@m.com', password='x', is_active=True)
        UserProfile.objects.filter(user=u).update(first_name='M', indemnity_accepted=True)
        self.client.force_login(u)
        resp = self.client.get('/app/map/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'id="map"')
```

**Step 2: Implement `apps/maps/views.py`**
```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings
from apps.bookings.models import Booking

@login_required
def map_screen(request):
    booking = (
        Booking.objects.filter(user=request.user)
        .exclude(status=Booking.Status.CANCELLED)
        .select_related('tour')
        .order_by('-tour__start_datetime')
        .first()
    )
    return render(request, 'app/map.html', {
        'booking': booking,
        'tour': booking.tour if booking else None,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
    })
```

**Step 3: Implement `templates/app/map.html`**
```html
{% extends 'base_app.html' %}
{% block title %}Map{% endblock %}
{% block main_class %}map-page{% endblock %}

{% block content %}
<div id="map-container" class="map-fullscreen">
  <div id="map" class="w-100 h-100"></div>
  {% if booking %}
  <a href="{% url 'bookings:itinerary_detail' booking.id %}" class="view-itinerary-btn">
    <i class="bi bi-chevron-up me-2"></i>VIEW ITINERARY
  </a>
  {% endif %}
</div>
{% endblock %}

{% block extra_js %}
{% if google_maps_api_key and tour %}
<script>
function initMap() {
  const map = new google.maps.Map(document.getElementById('map'), {
    center: { lat: {{ tour.location_lat }}, lng: {{ tour.location_lng }} },
    zoom: 13, mapTypeId: 'satellite',
    disableDefaultUI: true, zoomControl: true,
  });
  {% for item in tour.itinerary_items.all %}{% if item.location_lat and item.location_lng %}
  new google.maps.Marker({
    position: { lat: {{ item.location_lat }}, lng: {{ item.location_lng }} },
    map: map, label: '{{ forloop.counter }}',
  });
  {% endif %}{% endfor %}
}
</script>
<script src="https://maps.googleapis.com/maps/api/js?key={{ google_maps_api_key }}&callback=initMap" async defer></script>
{% else %}
<script>
(function() {
  const el = document.getElementById('map');
  el.style.background = 'linear-gradient(180deg, #2d4a2d, #1a3a2a)';
  const msg = document.createElement('p');
  msg.style.cssText = 'color:rgba(255,255,255,0.4);text-align:center;padding-top:40vh;font-size:14px;margin:0';
  msg.textContent = 'Map available after Google Maps setup (Phase 7)';
  el.appendChild(msg);
}());
</script>
{% endif %}
{% endblock %}
```

**Step 4: Add CSS**
```css
/* ---- Map screen ---- */
.map-page { padding-bottom: 0 !important; }
.map-fullscreen { position: relative; height: calc(100vh - 70px); }
#map { width: 100%; height: 100%; }
.view-itinerary-btn {
  position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%);
  background: white; border-radius: 24px; padding: 12px 24px;
  font-size: 13px; font-weight: 700; letter-spacing: 0.08em;
  text-decoration: none; color: var(--color-text);
  box-shadow: 0 4px 16px rgba(0,0,0,0.2); white-space: nowrap;
}
```

**Step 5: Run — PASS**
```
pytest apps/maps/tests/ -v
# Expected: 2 passed
```

**Step 6: Commit**
```bash
git add apps/maps/ templates/app/map.html static/css/app.css
git commit -m "feat: map screen — full-screen container, Google Maps JS-ready (Phase 7)"
```

---

## Task 22: Profile screen

**Files:**
- Modify: `apps/accounts/views.py` (implement profile_view properly)
- Modify: `templates/accounts/profile.html`
- Check: `templates/accounts/partials/settings_toggle.html`
- Modify: `static/css/app.css`
- Create: `apps/accounts/tests/test_profile_view.py`

**Step 1: Write tests** — `apps/accounts/tests/test_profile_view.py`:
```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile

def _make_user():
    User = get_user_model()
    u = User.objects.create_user(username='p@p.com', email='p@p.com', password='x', is_active=True)
    UserProfile.objects.filter(user=u).update(
        first_name='Gavin', last_name='Holder',
        phone_whatsapp='+27795029661', indemnity_accepted=True,
        fitness_level=3, role='GUEST',
    )
    return u

class ProfileViewTest(TestCase):
    def test_redirects_unauthenticated(self):
        self.assertIn('/accounts/login/', self.client.get('/accounts/profile/')['Location'])

    def test_shows_name_and_role(self):
        self.client.force_login(_make_user())
        resp = self.client.get('/accounts/profile/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Gavin Holder')
        self.assertContains(resp, 'Guest Traveller')

    def test_shows_phone(self):
        self.client.force_login(_make_user())
        resp = self.client.get('/accounts/profile/')
        self.assertContains(resp, '+27795029661')
```

**Step 2: Implement `profile_view` in `apps/accounts/views.py`** — replace the stub:
```python
@login_required
def profile_view(request):
    profile = request.user.profile
    fitness_labels = {1: 'Unfit', 2: 'Below Average', 3: 'Average', 4: 'Fit', 5: 'Very Fit'}
    return render(request, 'accounts/profile.html', {
        'profile': profile,
        'fitness_label': fitness_labels.get(profile.fitness_level, str(profile.fitness_level)),
        'dev_mode': getattr(settings, 'DEV_MODE', False),
    })
```

**Step 3: Implement `templates/accounts/profile.html`**
```html
{% extends 'base_app.html' %}
{% block title %}Profile{% endblock %}

{% block content %}
<div class="px-0">
  <div class="px-3 pt-3 pb-1">
    <a href="javascript:history.back()" class="text-muted"><i class="bi bi-chevron-left"></i></a>
  </div>

  <div class="profile-header-card mx-3 mb-4">
    <div class="d-flex justify-content-center">
      {% if profile.avatar %}
        <img src="{{ profile.avatar.url }}" class="profile-avatar-img" alt="avatar">
      {% else %}
        <div class="profile-avatar-circle bg-purple">{{ profile.initials|upper }}</div>
      {% endif %}
    </div>
    <h1 class="fw-bold text-white mb-0 mt-3" style="font-size:1.4rem">{{ profile.full_name }}</h1>
    <p class="mb-3" style="color:rgba(255,255,255,0.8)">{{ profile.get_role_display }}</p>
    <a href="{% url 'accounts:profile_setup_step' step=1 %}" class="profile-edit-btn">
      <i class="bi bi-pencil me-2"></i>Edit Profile
    </a>
  </div>

  <div class="px-3">
    <div class="card-oa mb-3">
      <div class="d-flex align-items-center mb-3">
        <i class="bi bi-person text-primary me-2"></i>
        <span class="fw-bold">Personal Details</span>
      </div>
      <div class="info-grid">
        <div class="info-item"><span class="label-xs">NAME</span><span class="fw-semibold">{{ profile.full_name }}</span></div>
        {% if profile.date_of_birth %}
        <div class="info-item"><span class="label-xs">DATE OF BIRTH</span><span class="fw-semibold">{{ profile.date_of_birth|date:"j F" }}</span></div>
        {% endif %}
        {% if profile.phone_whatsapp %}
        <div class="info-item"><span class="label-xs">PHONE</span><span class="fw-semibold">{{ profile.phone_whatsapp }}</span></div>
        {% endif %}
        <div class="info-item"><span class="label-xs">EMAIL</span><span class="fw-semibold">{{ request.user.email }}</span></div>
      </div>
    </div>

    <div class="card-oa mb-3">
      <div class="d-flex align-items-center mb-3">
        <i class="bi bi-heart-pulse text-danger me-2"></i>
        <span class="fw-bold">Health &amp; Diet</span>
      </div>
      <div class="info-grid">
        <div class="info-item"><span class="label-xs">FITNESS LEVEL</span><span class="fw-semibold">{{ fitness_label }}</span></div>
        <div class="info-item"><span class="label-xs">MEDICAL INFORMATION</span><span class="fw-semibold">{{ profile.medical_conditions|default:'None' }}</span></div>
        <div class="info-item"><span class="label-xs">DIETARY REQUIREMENTS</span><span class="fw-semibold">{{ profile.dietary_requirements|default:'None' }}</span></div>
      </div>
    </div>

    <div class="card-oa mb-3">
      <div class="d-flex align-items-center mb-3">
        <i class="bi bi-file-text text-warning me-2"></i>
        <span class="fw-bold">Notes</span>
      </div>
      <span class="label-xs">PERSONAL NOTES</span>
      <p class="fw-semibold mb-0">{{ profile.personal_notes|default:'No notes added' }}</p>
    </div>

    <div class="card-oa mb-3">
      <div class="d-flex align-items-center mb-3">
        <i class="bi bi-gear text-muted me-2"></i>
        <span class="fw-bold">App Settings</span>
      </div>
      {% include 'accounts/partials/settings_toggle.html' with field='location_enabled' label='Location Services' icon='geo-alt' %}
      <div class="my-2 border-bottom"></div>
      {% include 'accounts/partials/settings_toggle.html' with field='notifications_enabled' label='Notifications' icon='bell' %}
    </div>
  </div>
</div>
{% endblock %}
```

**Step 4: Check `templates/accounts/partials/settings_toggle.html`** — read it and verify it uses `hx-post="{% url 'accounts:settings_toggle' %}"`. If the partial references profile data but profile isn't passed as context from the `{% include %}` tag, ensure it uses `request.user.profile` directly (available via the request context processor). No changes needed if it already works.

**Step 5: Add CSS**
```css
/* ---- Profile screen ---- */
.profile-header-card {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  border-radius: 16px; padding: 24px 20px; text-align: center;
}
.profile-avatar-circle {
  width: 72px; height: 72px; border-radius: 50%;
  font-size: 28px; font-weight: 700;
  display: flex; align-items: center; justify-content: center; border: 3px solid white;
}
.profile-avatar-img { width: 72px; height: 72px; border-radius: 50%; object-fit: cover; border: 3px solid white; }
.profile-edit-btn {
  background: rgba(255,255,255,0.2); color: white; border-radius: 24px;
  padding: 8px 20px; font-size: 14px; font-weight: 600; text-decoration: none; display: inline-block;
}
.info-grid { display: flex; flex-direction: column; gap: 14px; }
.info-item { display: flex; flex-direction: column; }
```

**Step 6: Run — PASS**
```
pytest apps/accounts/tests/test_profile_view.py -v
# Expected: 3 passed
```

**Step 7: Run full Phase 6 suite**
```
pytest apps/landing/tests/ apps/bookings/tests/ apps/sos/tests/ apps/maps/tests/ apps/accounts/tests/ -v
# All should pass
```

**Step 8: Commit**
```bash
git add apps/accounts/ templates/accounts/profile.html static/css/app.css
git commit -m "feat: profile screen — header card, personal details, health, notes, settings toggles"
```

---

## Final verification

```bash
# Full test suite
pytest --tb=short -q

# Django system check
python manage.py check

# Manual smoke test
python manage.py runserver
# Test each screen: / → /app/itinerary/ → /app/sos/ → /app/map/ → /accounts/profile/
# Test join flow: enter a tour code on home screen
```

**After all pass:** Update `ROADMAP.md` — mark Tasks 15–20 as `[x]`.

```bash
git add ROADMAP.md
git commit -m "docs: mark Phase 6 PWA core screens as complete"
```
