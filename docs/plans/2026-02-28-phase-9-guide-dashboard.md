# Phase 9 — Guide Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a mobile-optimised guide/admin dashboard at `/guide/` covering Tours CRUD, Itinerary Builder, Guest Manifest, Activity Library, Guides tab, QR codes, and Photo Gallery.

**Architecture:** Separate base template (`templates/admin_panel/base.html`) distinct from the guest PWA; HTMX for inline forms and partial updates; Alpine.js for drag-to-reorder and modals; access gated by `UserProfile.role` in `{GUIDE, OPERATOR, ADMIN}` or `user.is_staff`. All views live in the existing `dashboard/` app (root-level, not under `apps/`).

**Tech Stack:** Django 6 · HTMX · Alpine.js · Bootstrap 5.3 · `qrcode[pil]` (pip install) · `Pillow` (already installed for avatars)

**Reference images:** `plannig/UI/guide portal/` folder (7 images) + 5 inline images sent in session. The tour list shows cards with name, dates, guest count, activity count, status badge, edit/delete actions. Tour detail has Itinerary | Guests sub-tabs. New Tour form has Name, Tour Code (auto-generated display), dates, capacity, location, description.

**Deferred to later phase:** Revenue overview (Chart.js), PDF export, Notification manager UI, full guide permissions toggle UI.

---

## Task 23: Dashboard Foundation

**Files:**
- Create: `dashboard/urls.py`
- Create: `dashboard/decorators.py`
- Create: `templates/admin_panel/base.html`
- Modify: `dashboard/views.py`
- Modify: `overberg_adventures/urls.py`
- Test: `dashboard/tests.py`

---

**Step 1: Write failing tests**

```python
# dashboard/tests.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile

User = get_user_model()


def make_user(email, role=UserProfile.Role.GUEST, is_staff=False):
    user = User.objects.create_user(username=email, email=email, password='pass')
    user.profile.role = role
    user.profile.save()
    if is_staff:
        user.is_staff = True
        user.save()
    return user


class DashboardAccessTest(TestCase):
    def test_guest_cannot_access_dashboard(self):
        """Guests get 403 forbidden."""
        user = make_user('guest@test.com', UserProfile.Role.GUEST)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertEqual(resp.status_code, 403)

    def test_guide_can_access_dashboard(self):
        user = make_user('guide@test.com', UserProfile.Role.GUIDE)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertEqual(resp.status_code, 200)

    def test_operator_can_access_dashboard(self):
        user = make_user('op@test.com', UserProfile.Role.OPERATOR)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertEqual(resp.status_code, 200)

    def test_admin_role_can_access_dashboard(self):
        user = make_user('admin@test.com', UserProfile.Role.ADMIN)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertEqual(resp.status_code, 200)

    def test_staff_can_access_dashboard(self):
        user = make_user('staff@test.com', is_staff=True)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertEqual(resp.status_code, 200)

    def test_unauthenticated_redirects_to_login(self):
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/', resp['Location'])

    def test_tours_list_renders_template(self):
        user = make_user('guide2@test.com', UserProfile.Role.GUIDE)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertTemplateUsed(resp, 'admin_panel/tours/list.html')
```

**Step 2: Run test — expect FAIL**

```bash
cd "D:\Projects\2026\overberg adventures"
.venv/Scripts/python manage.py test dashboard -v 2
```

Expected: `NoReverseMatch` or `ModuleNotFoundError` — dashboard has no urls.py yet.

---

**Step 3: Create `dashboard/decorators.py`**

```python
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

GUIDE_ROLES = {'GUIDE', 'OPERATOR', 'ADMIN'}


def guide_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if request.user.is_staff:
            return view_func(request, *args, **kwargs)
        profile = getattr(request.user, 'profile', None)
        if not profile or profile.role not in GUIDE_ROLES:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapped
```

---

**Step 4: Create `templates/admin_panel/base.html`**

The dashboard has its own full-page layout — NOT based on `base_app.html`. No bottom nav.
Tab navigation is rendered as a sticky top bar with 4 icon+label tabs.

```html
{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="theme-color" content="#1a3a2a">
  <title>{% block title %}Guide Dashboard{% endblock %} — Overstrand Adventures</title>
  <link rel="icon" href="{% static 'img/logo.png' %}">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
  <link rel="stylesheet" href="{% static 'css/dashboard.css' %}">
  {% block extra_head %}{% endblock %}
</head>
<body class="dashboard-body">

  {% if dev_mode %}
  <div class="dev-banner">DEV MODE &mdash; not for production</div>
  {% endif %}

  <header class="dashboard-header d-flex align-items-center px-3 py-2">
    <img src="{% static 'img/logo.png' %}" alt="Logo" height="32" class="me-2">
    <span class="fw-bold text-white flex-grow-1" style="font-size:1rem;">Guide Dashboard</span>
    <a href="/" class="text-white-50 small"><i class="bi bi-box-arrow-right"></i></a>
  </header>

  <nav class="dashboard-tabs d-flex border-bottom">
    <a href="{% url 'dashboard:tours_list' %}"
       class="dash-tab flex-fill text-center py-2 {% block tab_tours %}{% endblock %}">
      <i class="bi bi-map d-block fs-5"></i><span class="small">Tours</span>
    </a>
    <a href="{% url 'dashboard:activities_list' %}"
       class="dash-tab flex-fill text-center py-2 {% block tab_activities %}{% endblock %}">
      <i class="bi bi-lightning d-block fs-5"></i><span class="small">Activities</span>
    </a>
    <a href="{% url 'dashboard:guests_list' %}"
       class="dash-tab flex-fill text-center py-2 {% block tab_guests %}{% endblock %}">
      <i class="bi bi-people d-block fs-5"></i><span class="small">Guests</span>
    </a>
    <a href="{% url 'dashboard:guides_list' %}"
       class="dash-tab flex-fill text-center py-2 {% block tab_guides %}{% endblock %}">
      <i class="bi bi-person-badge d-block fs-5"></i><span class="small">Guides</span>
    </a>
  </nav>

  <main class="dashboard-main" id="dashboard-content">
    {% block content %}{% endblock %}
  </main>

  <div id="htmx-modal-target"></div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script src="https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.3/dist/cdn.min.js"></script>
  {% block extra_js %}{% endblock %}
</body>
</html>
```

---

**Step 5: Create `static/css/dashboard.css`**

```css
/* ── Dashboard base ── */
.dashboard-body {
  background: #f8f9fa;
  min-height: 100vh;
}

.dev-banner {
  background: #dc2626;
  color: #fff;
  text-align: center;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 0;
  letter-spacing: 0.5px;
}

.dashboard-header {
  background: linear-gradient(135deg, #1a3a2a, #2d5a3d);
  min-height: 52px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.dashboard-tabs {
  background: #fff;
  position: sticky;
  top: 52px;
  z-index: 99;
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
}

.dash-tab {
  color: #6c757d;
  text-decoration: none;
  font-size: 12px;
  transition: color .15s, border-bottom .15s;
  border-bottom: 3px solid transparent;
}

.dash-tab:hover,
.dash-tab.active {
  color: #F97316;
  border-bottom-color: #F97316;
}

.dashboard-main {
  padding: 16px;
  max-width: 600px;
  margin: 0 auto;
}

/* ── Tour cards ── */
.tour-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 1px 6px rgba(0,0,0,.07);
  border-left: 4px solid #F97316;
}

.tour-card.status-draft { border-left-color: #6c757d; }
.tour-card.status-active { border-left-color: #198754; }
.tour-card.status-completed { border-left-color: #0d6efd; }
.tour-card.status-cancelled { border-left-color: #dc3545; }

/* ── Itinerary builder ── */
.itinerary-row {
  background: #fff;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
  border: 1px solid #e9ecef;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: grab;
}

.itinerary-row:active { cursor: grabbing; }

.drag-handle {
  color: #adb5bd;
  font-size: 18px;
  flex-shrink: 0;
}

/* ── Inline HTMX forms ── */
.inline-form-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,.10);
  border-top: 3px solid #F97316;
}

/* ── Guest manifest ── */
.guest-row {
  background: #fff;
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 8px;
  border: 1px solid #e9ecef;
  display: flex;
  align-items: center;
  gap: 12px;
}

.guest-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #F97316;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
  flex-shrink: 0;
}

/* ── Photo gallery ── */
.photo-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
}

.photo-thumb {
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: 4px;
  width: 100%;
  cursor: pointer;
}

/* ── QR code display ── */
.qr-container {
  text-align: center;
  padding: 24px;
  background: #fff;
  border-radius: 12px;
}

/* ── FAB add button ── */
.fab-add {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: #F97316;
  color: #fff;
  font-size: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(249,115,22,.4);
  text-decoration: none;
  z-index: 50;
  transition: transform .15s;
}

.fab-add:hover { color: #fff; transform: scale(1.08); }
```

---

**Step 6: Create stub `templates/admin_panel/tours/list.html`**

```html
{% extends 'admin_panel/base.html' %}
{% block title %}Tours{% endblock %}
{% block tab_tours %}active{% endblock %}
{% block content %}
<h6 class="text-muted mb-3">Your Tours</h6>
{% for tour in tours %}
  <div class="tour-card status-{{ tour.status|lower }}">{{ tour.name }}</div>
{% empty %}
  <p class="text-muted text-center">No tours yet.</p>
{% endfor %}
{% endblock %}
```

(This stub is enough for the access tests to pass. Full list template is built in Task 24.)

---

**Step 7: Create `dashboard/views.py` index + tours_list stub**

```python
from django.shortcuts import render, redirect
from .decorators import guide_required
from apps.tours.models import Tour


@guide_required
def index(request):
    return redirect('dashboard:tours_list')


@guide_required
def tours_list(request):
    tours = Tour.objects.select_related('guide__profile').order_by('-start_datetime')
    if not request.user.is_staff:
        profile = request.user.profile
        if profile.role == 'GUIDE':
            tours = tours.filter(guide=request.user)
    return render(request, 'admin_panel/tours/list.html', {
        'tours': tours,
        'dev_mode': getattr(__import__('django.conf', fromlist=['settings']).conf.settings, 'DEV_MODE', False),
    })
```

Wait — `dev_mode` is a context processor already. Let me check if there's one.

Actually from reading `base_app.html` — it uses `{% if dev_mode %}`. This comes from a context processor. Let me keep the pattern consistent and add `dev_mode` in a context processor instead of in every view. For now, pass it manually — but note that a context processor would be cleaner (amendment task if needed).

---

**Step 8: Create `dashboard/urls.py`**

```python
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('tours/', views.tours_list, name='tours_list'),
    # Stubs for tab URLs (needed for base template reverse() calls)
    path('activities/', views.activities_list, name='activities_list'),
    path('guests/', views.guests_list, name='guests_list'),
    path('guides/', views.guides_list, name='guides_list'),
]
```

Add these stub views to `dashboard/views.py`:

```python
@guide_required
def activities_list(request):
    return render(request, 'admin_panel/activities/list.html', {'dev_mode': _dev_mode()})

@guide_required
def guests_list(request):
    return render(request, 'admin_panel/guests/list.html', {'dev_mode': _dev_mode()})

@guide_required
def guides_list(request):
    return render(request, 'admin_panel/guides/list.html', {'dev_mode': _dev_mode()})


def _dev_mode():
    from django.conf import settings
    return getattr(settings, 'DEV_MODE', False)
```

And create stub templates:
- `templates/admin_panel/activities/list.html` (extends base, tab_activities active)
- `templates/admin_panel/guests/list.html` (extends base, tab_guests active)
- `templates/admin_panel/guides/list.html` (extends base, tab_guides active)

---

**Step 9: Wire into `overberg_adventures/urls.py`**

Add after the `path('accounts/', ...)` line:

```python
path('guide/', include('dashboard.urls', namespace='dashboard')),
```

---

**Step 10: Run tests — expect PASS**

```bash
.venv/Scripts/python manage.py test dashboard -v 2
```

Expected: 7 tests, all PASS.

---

**Step 11: Commit**

```bash
git add dashboard/ templates/admin_panel/ static/css/dashboard.css overberg_adventures/urls.py
git commit -m "feat: guide dashboard foundation - base template, URL routing, guide_required decorator"
```

---

## Task 24: Tours Tab — List View

**Files:**
- Modify: `dashboard/views.py` — tours_list (full implementation)
- Modify: `templates/admin_panel/tours/list.html` (full)
- Create: `templates/admin_panel/tours/partials/tour_card.html`
- Test: `dashboard/tests.py`

---

**Step 1: Write failing tests**

Add to `dashboard/tests.py`:

```python
from apps.tours.models import Tour
from django.utils import timezone
from datetime import timedelta


def make_tour(guide, name='Test Tour', status=Tour.Status.ACTIVE):
    return Tour.objects.create(
        name=name,
        guide=guide,
        start_datetime=timezone.now() + timedelta(days=3),
        location_name='Test Beach',
        capacity=10,
        status=status,
    )


class ToursListTest(TestCase):
    def setUp(self):
        self.guide = make_user('guide@tours.com', UserProfile.Role.GUIDE)
        self.client.force_login(self.guide)

    def test_shows_guide_own_tours_only(self):
        """Guides only see their own tours."""
        other_guide = make_user('other@tours.com', UserProfile.Role.GUIDE)
        t1 = make_tour(self.guide, 'My Tour')
        make_tour(other_guide, 'Their Tour')
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertContains(resp, 'My Tour')
        self.assertNotContains(resp, 'Their Tour')

    def test_admin_sees_all_tours(self):
        """Admin/staff sees tours from all guides."""
        admin = make_user('admin@tours.com', is_staff=True)
        self.client.force_login(admin)
        other = make_user('g2@tours.com', UserProfile.Role.GUIDE)
        make_tour(self.guide, 'Tour A')
        make_tour(other, 'Tour B')
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertContains(resp, 'Tour A')
        self.assertContains(resp, 'Tour B')

    def test_shows_empty_state(self):
        """Empty state message when no tours."""
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertContains(resp, 'No tours')

    def test_shows_guest_count_badge(self):
        """Tour card shows confirmed guest count."""
        from apps.bookings.models import Booking
        guest = make_user('g@guest.com', UserProfile.Role.GUEST)
        tour = make_tour(self.guide, 'Beach Tour')
        Booking.objects.create(tour=tour, user=guest, status=Booking.Status.CONFIRMED)
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertContains(resp, '1')  # guest count
```

**Step 2: Run — expect FAIL**

```bash
.venv/Scripts/python manage.py test dashboard.ToursListTest -v 2
```

---

**Step 3: Update `dashboard/views.py` — full tours_list**

```python
@guide_required
def tours_list(request):
    from apps.bookings.models import Booking
    from django.db.models import Count, Q
    tours = (
        Tour.objects
        .select_related('guide__profile')
        .annotate(
            guest_count=Count(
                'bookings',
                filter=Q(bookings__status__in=['RSVP_PENDING', 'CONFIRMED'])
            ),
            activity_count=Count('itinerary_items'),
        )
        .order_by('-start_datetime')
    )
    profile = getattr(request.user, 'profile', None)
    if not request.user.is_staff and profile and profile.role == 'GUIDE':
        tours = tours.filter(guide=request.user)
    return render(request, 'admin_panel/tours/list.html', {
        'tours': tours,
        'dev_mode': _dev_mode(),
    })
```

---

**Step 4: Replace `templates/admin_panel/tours/list.html`**

```html
{% extends 'admin_panel/base.html' %}
{% block title %}Tours{% endblock %}
{% block tab_tours %}active{% endblock %}

{% block content %}
<div class="d-flex align-items-center mb-3">
  <h6 class="mb-0 fw-bold flex-grow-1">Your Tours</h6>
  <a href="{% url 'dashboard:tour_create' %}" class="btn btn-sm btn-warning fw-bold">
    <i class="bi bi-plus-lg me-1"></i>New Tour
  </a>
</div>

{% for tour in tours %}
  {% include 'admin_panel/tours/partials/tour_card.html' with tour=tour only %}
{% empty %}
  <div class="text-center text-muted py-5">
    <i class="bi bi-map fs-1 d-block mb-2 opacity-25"></i>
    <p class="mb-3">No tours yet.</p>
    <a href="{% url 'dashboard:tour_create' %}" class="btn btn-warning">Create your first tour</a>
  </div>
{% endfor %}
{% endblock %}
```

---

**Step 5: Create `templates/admin_panel/tours/partials/tour_card.html`**

```html
{% load tz %}
<div class="tour-card status-{{ tour.status|lower }}">
  <div class="d-flex align-items-start justify-content-between mb-1">
    <div class="fw-bold" style="font-size:15px;">{{ tour.name }}</div>
    <span class="badge rounded-pill ms-2
      {% if tour.status == 'ACTIVE' %}bg-success
      {% elif tour.status == 'DRAFT' %}bg-secondary
      {% elif tour.status == 'COMPLETED' %}bg-primary
      {% else %}bg-danger{% endif %}
    " style="font-size:10px;">{{ tour.get_status_display }}</span>
  </div>

  <div class="text-muted small mb-2">
    <i class="bi bi-calendar3 me-1"></i>{{ tour.start_datetime|date:"d M Y" }}
    {% if tour.end_datetime %}&nbsp;→ {{ tour.end_datetime|date:"d M Y" }}{% endif %}
  </div>

  <div class="d-flex gap-3 small text-muted mb-3">
    <span><i class="bi bi-people me-1"></i>{{ tour.guest_count }}/{{ tour.capacity }}</span>
    <span><i class="bi bi-list-check me-1"></i>{{ tour.activity_count }} activities</span>
    <span><i class="bi bi-geo-alt me-1"></i>{{ tour.location_name|truncatechars:20 }}</span>
  </div>

  <div class="d-flex gap-2">
    <a href="{% url 'dashboard:tour_detail' tour.pk %}" class="btn btn-sm btn-outline-secondary flex-fill">
      <i class="bi bi-eye me-1"></i>Manage
    </a>
    <a href="{% url 'dashboard:tour_edit' tour.pk %}" class="btn btn-sm btn-outline-warning">
      <i class="bi bi-pencil"></i>
    </a>
    <a href="{% url 'dashboard:tour_qr' tour.pk %}" class="btn btn-sm btn-outline-secondary">
      <i class="bi bi-qr-code"></i>
    </a>
    <a href="{% url 'dashboard:tour_delete' tour.pk %}"
       class="btn btn-sm btn-outline-danger"
       hx-delete="{% url 'dashboard:tour_delete' tour.pk %}"
       hx-confirm="Delete {{ tour.name }}? This will also delete all itinerary items and bookings."
       hx-target="closest .tour-card"
       hx-swap="outerHTML swap:0.3s">
      <i class="bi bi-trash"></i>
    </a>
  </div>
</div>
```

---

**Step 6: Add new URL stubs to `dashboard/urls.py`** (needed for template reverse() calls)

```python
path('tours/create/', views.tour_create, name='tour_create'),
path('tours/<int:pk>/', views.tour_detail, name='tour_detail'),
path('tours/<int:pk>/edit/', views.tour_edit, name='tour_edit'),
path('tours/<int:pk>/delete/', views.tour_delete, name='tour_delete'),
path('tours/<int:pk>/qr/', views.tour_qr, name='tour_qr'),
```

Add stub views to `dashboard/views.py`:

```python
@guide_required
def tour_create(request):
    return render(request, 'admin_panel/tours/form.html', {'dev_mode': _dev_mode()})

@guide_required
def tour_detail(request, pk):
    from django.shortcuts import get_object_or_404
    tour = get_object_or_404(Tour, pk=pk)
    return render(request, 'admin_panel/tours/detail.html', {'tour': tour, 'dev_mode': _dev_mode()})

@guide_required
def tour_edit(request, pk):
    from django.shortcuts import get_object_or_404
    tour = get_object_or_404(Tour, pk=pk)
    return render(request, 'admin_panel/tours/form.html', {'tour': tour, 'dev_mode': _dev_mode()})

@guide_required
def tour_delete(request, pk):
    from django.shortcuts import get_object_or_404
    from django.http import HttpResponse
    tour = get_object_or_404(Tour, pk=pk)
    if request.method in ('POST', 'DELETE'):
        tour.delete()
        return HttpResponse('')
    return HttpResponse(status=405)

@guide_required
def tour_qr(request, pk):
    from django.shortcuts import get_object_or_404
    tour = get_object_or_404(Tour, pk=pk)
    return render(request, 'admin_panel/tours/qr.html', {'tour': tour, 'dev_mode': _dev_mode()})
```

Create minimal stub templates (`form.html`, `detail.html`, `qr.html`) extending base so reverse() works.

---

**Step 7: Run tests — expect PASS**

```bash
.venv/Scripts/python manage.py test dashboard -v 2
```

---

**Step 8: Commit**

```bash
git add dashboard/ templates/admin_panel/
git commit -m "feat: tours list tab with annotated cards (guest count, activity count, status)"
```

---

## Task 25: Tour CRUD — Create & Edit

**Files:**
- Create: `dashboard/forms.py`
- Modify: `dashboard/views.py` — tour_create, tour_edit (full)
- Create: `templates/admin_panel/tours/form.html`
- Test: `dashboard/tests.py`

---

**Step 1: Write failing tests**

```python
class TourCRUDTest(TestCase):
    def setUp(self):
        self.guide = make_user('guide@crud.com', UserProfile.Role.GUIDE)
        self.client.force_login(self.guide)

    def test_create_tour_get_shows_form(self):
        resp = self.client.get(reverse('dashboard:tour_create'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Tour Name')

    def test_create_tour_post_creates_and_redirects(self):
        resp = self.client.post(reverse('dashboard:tour_create'), {
            'name': 'Whale Watching',
            'start_datetime': '2026-04-01 09:00',
            'location_name': 'Hermanus',
            'capacity': 12,
            'status': 'DRAFT',
            'description': '',
        })
        self.assertEqual(Tour.objects.count(), 1)
        tour = Tour.objects.first()
        self.assertEqual(tour.guide, self.guide)
        self.assertRedirects(resp, reverse('dashboard:tour_detail', args=[tour.pk]))

    def test_create_tour_auto_assigns_guide(self):
        self.client.post(reverse('dashboard:tour_create'), {
            'name': 'Hike',
            'start_datetime': '2026-05-01 07:00',
            'location_name': 'Kogelberg',
            'capacity': 8,
            'status': 'DRAFT',
            'description': '',
        })
        tour = Tour.objects.first()
        self.assertEqual(tour.guide, self.guide)

    def test_edit_tour_updates_fields(self):
        tour = make_tour(self.guide, 'Old Name')
        resp = self.client.post(reverse('dashboard:tour_edit', args=[tour.pk]), {
            'name': 'New Name',
            'start_datetime': '2026-06-01 08:00',
            'location_name': 'Bettys Bay',
            'capacity': 15,
            'status': 'ACTIVE',
            'description': 'Updated',
        })
        tour.refresh_from_db()
        self.assertEqual(tour.name, 'New Name')
        self.assertRedirects(resp, reverse('dashboard:tour_detail', args=[tour.pk]))

    def test_delete_tour_removes_it(self):
        tour = make_tour(self.guide)
        resp = self.client.delete(reverse('dashboard:tour_delete', args=[tour.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Tour.objects.filter(pk=tour.pk).exists())
```

**Step 2: Run — expect FAIL**

```bash
.venv/Scripts/python manage.py test dashboard.TourCRUDTest -v 2
```

---

**Step 3: Create `dashboard/forms.py`**

```python
from django import forms
from apps.tours.models import Tour


class TourForm(forms.ModelForm):
    start_datetime = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M'],
    )
    end_datetime = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M'],
    )

    class Meta:
        model = Tour
        fields = [
            'name', 'description', 'start_datetime', 'end_datetime',
            'location_name', 'capacity', 'status',
            'min_fitness_level', 'rsvp_deadline_hours',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
```

---

**Step 4: Update `dashboard/views.py` — tour_create full**

```python
from .forms import TourForm


@guide_required
def tour_create(request):
    if request.method == 'POST':
        form = TourForm(request.POST)
        if form.is_valid():
            tour = form.save(commit=False)
            if not request.user.is_staff:
                tour.guide = request.user
            tour.save()
            return redirect('dashboard:tour_detail', pk=tour.pk)
    else:
        form = TourForm()
    return render(request, 'admin_panel/tours/form.html', {
        'form': form,
        'dev_mode': _dev_mode(),
    })


@guide_required
def tour_edit(request, pk):
    from django.shortcuts import get_object_or_404
    tour = get_object_or_404(Tour, pk=pk)
    if request.method == 'POST':
        form = TourForm(request.POST, instance=tour)
        if form.is_valid():
            form.save()
            return redirect('dashboard:tour_detail', pk=tour.pk)
    else:
        form = TourForm(instance=tour)
    return render(request, 'admin_panel/tours/form.html', {
        'form': form,
        'tour': tour,
        'dev_mode': _dev_mode(),
    })
```

---

**Step 5: Create `templates/admin_panel/tours/form.html`**

```html
{% extends 'admin_panel/base.html' %}
{% block title %}{% if tour %}Edit Tour{% else %}New Tour{% endif %}{% endblock %}
{% block tab_tours %}active{% endblock %}

{% block content %}
<div class="d-flex align-items-center mb-3">
  <a href="{% if tour %}{% url 'dashboard:tour_detail' tour.pk %}{% else %}{% url 'dashboard:tours_list' %}{% endif %}"
     class="btn btn-sm btn-link ps-0 text-muted">
    <i class="bi bi-arrow-left me-1"></i>Back
  </a>
  <h6 class="mb-0 fw-bold flex-grow-1">
    {% if tour %}Edit Tour{% else %}New Tour{% endif %}
  </h6>
</div>

{% if tour %}
<div class="inline-form-card mb-3">
  <div class="text-muted small mb-1">Tour Code</div>
  <div class="fw-bold fs-5 font-monospace">{{ tour.tour_code }}</div>
  <div class="text-muted" style="font-size:11px;">Assigned at tour creation. Share with guests after payment.</div>
</div>
{% endif %}

<div class="inline-form-card">
  <form method="post" novalidate>
    {% csrf_token %}

    {% for field in form %}
    <div class="mb-3">
      <label class="form-label small fw-bold" for="{{ field.id_for_label }}">{{ field.label }}</label>
      {% if field.errors %}
        {{ field|add_class:"form-control is-invalid" }}
        <div class="invalid-feedback">{{ field.errors.0 }}</div>
      {% else %}
        {{ field }}
      {% endif %}
      {% if field.help_text %}
        <div class="form-text">{{ field.help_text }}</div>
      {% endif %}
    </div>
    {% endfor %}

    <div class="d-flex gap-2 mt-4">
      <button type="submit" class="btn btn-warning fw-bold flex-fill">
        {% if tour %}Save Changes{% else %}Create Tour{% endif %}
      </button>
      <a href="{% if tour %}{% url 'dashboard:tour_detail' tour.pk %}{% else %}{% url 'dashboard:tours_list' %}{% endif %}"
         class="btn btn-outline-secondary">Cancel</a>
    </div>
  </form>
</div>
{% endblock %}

{% block extra_js %}
<script>
// Apply Bootstrap classes to form inputs (since we can't use add_class without widget)
document.querySelectorAll('input:not([type=checkbox]):not([type=radio]), select, textarea').forEach(el => {
  if (!el.classList.contains('form-control') && !el.classList.contains('form-select')) {
    el.classList.add(el.tagName === 'SELECT' ? 'form-select' : 'form-control');
  }
});
document.querySelectorAll('input[type=checkbox]').forEach(el => el.classList.add('form-check-input'));
</script>
{% endblock %}
```

---

**Step 6: Run tests — expect PASS**

```bash
.venv/Scripts/python manage.py test dashboard -v 2
```

---

**Step 7: Commit**

```bash
git add dashboard/ templates/admin_panel/tours/form.html
git commit -m "feat: tour create/edit/delete CRUD with TourForm"
```

---

## Task 26: Tour Detail — Sub-tabs Shell + Overview

**Files:**
- Modify: `dashboard/views.py` — tour_detail (full)
- Create: `templates/admin_panel/tours/detail.html`
- Create: `templates/admin_panel/tours/partials/overview_tab.html`
- Test: `dashboard/tests.py`

---

**Step 1: Write failing tests**

```python
class TourDetailTest(TestCase):
    def setUp(self):
        self.guide = make_user('guide@detail.com', UserProfile.Role.GUIDE)
        self.client.force_login(self.guide)
        self.tour = make_tour(self.guide, 'Detail Tour')

    def test_detail_shows_tour_name(self):
        resp = self.client.get(reverse('dashboard:tour_detail', args=[self.tour.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Detail Tour')

    def test_detail_shows_sub_tabs(self):
        resp = self.client.get(reverse('dashboard:tour_detail', args=[self.tour.pk]))
        self.assertContains(resp, 'Itinerary')
        self.assertContains(resp, 'Guests')
        self.assertContains(resp, 'Overview')

    def test_detail_shows_tour_code(self):
        resp = self.client.get(reverse('dashboard:tour_detail', args=[self.tour.pk]))
        self.assertContains(resp, self.tour.tour_code)

    def test_detail_shows_capacity(self):
        resp = self.client.get(reverse('dashboard:tour_detail', args=[self.tour.pk]))
        self.assertContains(resp, str(self.tour.capacity))

    def test_guide_cannot_access_other_guide_tour(self):
        other = make_user('other@detail.com', UserProfile.Role.GUIDE)
        other_tour = make_tour(other, 'Other Tour')
        resp = self.client.get(reverse('dashboard:tour_detail', args=[other_tour.pk]))
        self.assertEqual(resp.status_code, 403)
```

**Step 2: Run — expect FAIL**

```bash
.venv/Scripts/python manage.py test dashboard.TourDetailTest -v 2
```

---

**Step 3: Update `dashboard/views.py` — tour_detail full**

```python
from django.core.exceptions import PermissionDenied


@guide_required
def tour_detail(request, pk):
    from django.shortcuts import get_object_or_404
    from apps.bookings.models import Booking
    from apps.tours.models import ItineraryItem
    tour = get_object_or_404(Tour.objects.select_related('guide__profile'), pk=pk)
    # Permission: guides can only see their own tours
    profile = getattr(request.user, 'profile', None)
    if not request.user.is_staff and profile and profile.role == 'GUIDE':
        if tour.guide != request.user:
            raise PermissionDenied

    active_tab = request.GET.get('tab', 'itinerary')
    bookings = Booking.objects.filter(tour=tour).select_related('user__profile').order_by('invited_at')
    itinerary_items = ItineraryItem.objects.filter(tour=tour).select_related('category')

    # Group itinerary by day
    items_by_day = {}
    for item in itinerary_items:
        items_by_day.setdefault(item.day, []).append(item)
    items_by_day = dict(sorted(items_by_day.items()))

    return render(request, 'admin_panel/tours/detail.html', {
        'tour': tour,
        'active_tab': active_tab,
        'bookings': bookings,
        'items_by_day': items_by_day,
        'dev_mode': _dev_mode(),
    })
```

---

**Step 4: Create `templates/admin_panel/tours/detail.html`**

```html
{% extends 'admin_panel/base.html' %}
{% block title %}{{ tour.name }}{% endblock %}
{% block tab_tours %}active{% endblock %}

{% block content %}
<div class="d-flex align-items-center mb-3">
  <a href="{% url 'dashboard:tours_list' %}" class="btn btn-sm btn-link ps-0 text-muted">
    <i class="bi bi-arrow-left me-1"></i>Tours
  </a>
  <h6 class="mb-0 fw-bold flex-grow-1 text-truncate">{{ tour.name }}</h6>
  <a href="{% url 'dashboard:tour_edit' tour.pk %}" class="btn btn-sm btn-outline-warning ms-2">
    <i class="bi bi-pencil"></i>
  </a>
</div>

<!-- Sub-tabs -->
<ul class="nav nav-tabs mb-3" role="tablist">
  <li class="nav-item">
    <a class="nav-link {% if active_tab == 'itinerary' %}active{% endif %}"
       href="?tab=itinerary">Itinerary</a>
  </li>
  <li class="nav-item">
    <a class="nav-link {% if active_tab == 'guests' %}active{% endif %}"
       href="?tab=guests">
      Guests
      <span class="badge bg-secondary ms-1">{{ bookings.count }}</span>
    </a>
  </li>
  <li class="nav-item">
    <a class="nav-link {% if active_tab == 'overview' %}active{% endif %}"
       href="?tab=overview">Overview</a>
  </li>
</ul>

<!-- Tab content -->
{% if active_tab == 'itinerary' %}
  {% include 'admin_panel/tours/partials/itinerary_tab.html' %}
{% elif active_tab == 'guests' %}
  {% include 'admin_panel/tours/partials/guests_tab.html' %}
{% else %}
  {% include 'admin_panel/tours/partials/overview_tab.html' %}
{% endif %}

{% endblock %}
```

---

**Step 5: Create `templates/admin_panel/tours/partials/overview_tab.html`**

```html
<div class="inline-form-card mb-3">
  <div class="row g-3 text-center">
    <div class="col-4">
      <div class="fw-bold fs-4">{{ bookings.count }}</div>
      <div class="text-muted" style="font-size:11px;">Guests</div>
    </div>
    <div class="col-4">
      <div class="fw-bold fs-4">{{ tour.spots_remaining }}</div>
      <div class="text-muted" style="font-size:11px;">Spots Left</div>
    </div>
    <div class="col-4">
      <div class="fw-bold fs-4">{{ tour.capacity }}</div>
      <div class="text-muted" style="font-size:11px;">Capacity</div>
    </div>
  </div>
</div>

<div class="inline-form-card mb-3">
  <div class="small text-muted mb-1">Tour Code</div>
  <div class="fw-bold font-monospace fs-5">{{ tour.tour_code }}</div>
</div>

<div class="inline-form-card mb-3">
  <div class="small text-muted mb-1">Dates</div>
  <div>{{ tour.start_datetime|date:"D d M Y, H:i" }}</div>
  {% if tour.end_datetime %}
  <div class="text-muted small">→ {{ tour.end_datetime|date:"D d M Y, H:i" }}</div>
  {% endif %}
</div>

<div class="inline-form-card mb-3">
  <div class="small text-muted mb-1">Location</div>
  <div>{{ tour.location_name }}</div>
</div>

{% if tour.description %}
<div class="inline-form-card mb-3">
  <div class="small text-muted mb-1">Description</div>
  <p class="mb-0">{{ tour.description }}</p>
</div>
{% endif %}

<div class="d-flex gap-2 mt-3">
  <a href="{% url 'dashboard:tour_qr' tour.pk %}" class="btn btn-outline-secondary flex-fill">
    <i class="bi bi-qr-code me-1"></i>QR Code
  </a>
  <a href="{% url 'dashboard:tour_delete' tour.pk %}"
     class="btn btn-outline-danger"
     onclick="return confirm('Delete {{ tour.name|escapejs }}? This cannot be undone.')">
    <i class="bi bi-trash me-1"></i>Delete Tour
  </a>
</div>
```

**Step 6: Create stub `templates/admin_panel/tours/partials/guests_tab.html`**

```html
<p class="text-muted text-center py-4">Guests tab coming in Task 27.</p>
```

Create stub `templates/admin_panel/tours/partials/itinerary_tab.html`:

```html
<p class="text-muted text-center py-4">Itinerary builder coming in Task 27.</p>
```

---

**Step 7: Run tests — expect PASS**

```bash
.venv/Scripts/python manage.py test dashboard -v 2
```

---

**Step 8: Commit**

```bash
git add dashboard/ templates/admin_panel/tours/
git commit -m "feat: tour detail view with Itinerary/Guests/Overview sub-tabs"
```

---

## Task 27: Itinerary Builder

**Files:**
- Modify: `dashboard/forms.py` — ItineraryItemForm
- Modify: `dashboard/urls.py` — itinerary CRUD + reorder URLs
- Modify: `dashboard/views.py` — itinerary_add, itinerary_edit, itinerary_delete, itinerary_reorder
- Modify: `templates/admin_panel/tours/partials/itinerary_tab.html` (full)
- Create: `templates/admin_panel/tours/partials/itinerary_item_row.html`
- Create: `templates/admin_panel/tours/partials/itinerary_item_form.html`
- Test: `dashboard/tests.py`

---

**Step 1: Write failing tests**

```python
from apps.tours.models import ItineraryItem, ActivityCategory
from django.utils import timezone
from datetime import time


def make_category(name='Hike'):
    return ActivityCategory.objects.create(name=name, icon='geo-alt', colour='#198754')


class ItineraryBuilderTest(TestCase):
    def setUp(self):
        self.guide = make_user('guide@itinerary.com', UserProfile.Role.GUIDE)
        self.client.force_login(self.guide)
        self.tour = make_tour(self.guide)
        self.category = make_category()

    def test_add_item_creates_itinerary_item(self):
        resp = self.client.post(
            reverse('dashboard:itinerary_add', args=[self.tour.pk]),
            {
                'title': 'Morning Hike',
                'day': 1,
                'order': 0,
                'start_time': '07:00',
                'duration_minutes': 120,
                'category': self.category.pk,
                'location_name': 'Kogelberg Peak',
                'description': '',
                'difficulty': 'MODERATE',
            }
        )
        self.assertEqual(ItineraryItem.objects.count(), 1)
        item = ItineraryItem.objects.first()
        self.assertEqual(item.title, 'Morning Hike')
        self.assertEqual(item.tour, self.tour)

    def test_add_item_htmx_returns_partial(self):
        resp = self.client.post(
            reverse('dashboard:itinerary_add', args=[self.tour.pk]),
            {
                'title': 'Beach Walk', 'day': 1, 'order': 0,
                'start_time': '09:00', 'duration_minutes': 60,
                'category': self.category.pk, 'location_name': 'Beach',
                'description': '', 'difficulty': 'EASY',
            },
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Beach Walk')

    def test_edit_item_updates_title(self):
        item = ItineraryItem.objects.create(
            tour=self.tour, title='Old Title', day=1, order=0,
            start_time=time(8, 0), duration_minutes=60, difficulty='EASY',
            category=self.category,
        )
        self.client.post(
            reverse('dashboard:itinerary_edit', args=[self.tour.pk, item.pk]),
            {
                'title': 'New Title', 'day': 1, 'order': 0,
                'start_time': '08:00', 'duration_minutes': 90,
                'category': self.category.pk, 'location_name': '',
                'description': '', 'difficulty': 'EASY',
            }
        )
        item.refresh_from_db()
        self.assertEqual(item.title, 'New Title')

    def test_delete_item_removes_it(self):
        item = ItineraryItem.objects.create(
            tour=self.tour, title='To Delete', day=1, order=0,
            start_time=time(8, 0), duration_minutes=30, difficulty='EASY',
        )
        resp = self.client.delete(
            reverse('dashboard:itinerary_delete', args=[self.tour.pk, item.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(ItineraryItem.objects.filter(pk=item.pk).exists())

    def test_guide_cannot_edit_other_tour_item(self):
        other = make_user('other@itinerary.com', UserProfile.Role.GUIDE)
        other_tour = make_tour(other)
        item = ItineraryItem.objects.create(
            tour=other_tour, title='Restricted', day=1, order=0,
            start_time=time(9, 0), duration_minutes=60, difficulty='EASY',
        )
        resp = self.client.post(
            reverse('dashboard:itinerary_edit', args=[other_tour.pk, item.pk]),
            {'title': 'Hacked', 'day': 1, 'order': 0, 'start_time': '09:00',
             'duration_minutes': 60, 'category': '', 'location_name': '', 'description': '', 'difficulty': 'EASY'},
        )
        self.assertEqual(resp.status_code, 403)
```

**Step 2: Run — expect FAIL**

```bash
.venv/Scripts/python manage.py test dashboard.ItineraryBuilderTest -v 2
```

---

**Step 3: Add `ItineraryItemForm` to `dashboard/forms.py`**

```python
from apps.tours.models import ItineraryItem


class ItineraryItemForm(forms.ModelForm):
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
    )

    class Meta:
        model = ItineraryItem
        fields = [
            'title', 'description', 'category', 'day', 'order',
            'start_time', 'duration_minutes', 'location_name',
            'difficulty', 'distance_km',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'day': forms.NumberInput(attrs={'min': 1}),
            'order': forms.HiddenInput(),
        }
```

---

**Step 4: Add itinerary URL patterns to `dashboard/urls.py`**

```python
path('tours/<int:tour_pk>/itinerary/add/', views.itinerary_add, name='itinerary_add'),
path('tours/<int:tour_pk>/itinerary/<int:item_pk>/edit/', views.itinerary_edit, name='itinerary_edit'),
path('tours/<int:tour_pk>/itinerary/<int:item_pk>/delete/', views.itinerary_delete, name='itinerary_delete'),
path('tours/<int:tour_pk>/itinerary/reorder/', views.itinerary_reorder, name='itinerary_reorder'),
```

---

**Step 5: Add itinerary views to `dashboard/views.py`**

```python
from apps.tours.models import ItineraryItem
from .forms import TourForm, ItineraryItemForm


def _get_tour_for_guide(request, tour_pk):
    """Get tour, enforce guide ownership. Raises PermissionDenied for other guide's tours."""
    from django.shortcuts import get_object_or_404
    tour = get_object_or_404(Tour, pk=tour_pk)
    profile = getattr(request.user, 'profile', None)
    if not request.user.is_staff and profile and profile.role == 'GUIDE':
        if tour.guide != request.user:
            raise PermissionDenied
    return tour


@guide_required
def itinerary_add(request, tour_pk):
    tour = _get_tour_for_guide(request, tour_pk)
    if request.method == 'POST':
        form = ItineraryItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.tour = tour
            item.save()
            # HTMX: return the new item row partial
            if request.headers.get('HX-Request'):
                return render(request, 'admin_panel/tours/partials/itinerary_item_row.html', {'item': item})
            return redirect(f"{reverse('dashboard:tour_detail', args=[tour.pk])}?tab=itinerary")
    else:
        form = ItineraryItemForm(initial={'day': 1, 'order': 0})
    return render(request, 'admin_panel/tours/partials/itinerary_item_form.html', {
        'form': form, 'tour': tour, 'dev_mode': _dev_mode(),
    })


@guide_required
def itinerary_edit(request, tour_pk, item_pk):
    from django.shortcuts import get_object_or_404
    tour = _get_tour_for_guide(request, tour_pk)
    item = get_object_or_404(ItineraryItem, pk=item_pk, tour=tour)
    if request.method == 'POST':
        form = ItineraryItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return render(request, 'admin_panel/tours/partials/itinerary_item_row.html', {'item': item})
            return redirect(f"{reverse('dashboard:tour_detail', args=[tour.pk])}?tab=itinerary")
    else:
        form = ItineraryItemForm(instance=item)
    return render(request, 'admin_panel/tours/partials/itinerary_item_form.html', {
        'form': form, 'tour': tour, 'item': item, 'dev_mode': _dev_mode(),
    })


@guide_required
def itinerary_delete(request, tour_pk, item_pk):
    from django.shortcuts import get_object_or_404
    from django.http import HttpResponse
    tour = _get_tour_for_guide(request, tour_pk)
    item = get_object_or_404(ItineraryItem, pk=item_pk, tour=tour)
    if request.method in ('POST', 'DELETE'):
        item.delete()
        return HttpResponse('')
    return HttpResponse(status=405)


@guide_required
def itinerary_reorder(request, tour_pk):
    """HTMX POST: receive JSON list of {id, order} pairs and update DB."""
    import json
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    tour = _get_tour_for_guide(request, tour_pk)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'invalid JSON'}, status=400)
        for entry in data:
            ItineraryItem.objects.filter(pk=entry['id'], tour=tour).update(order=entry['order'])
        return JsonResponse({'ok': True})
    return JsonResponse({'error': 'method not allowed'}, status=405)
```

Note: `reverse` needs to be imported at top of views.py:
```python
from django.urls import reverse
```

---

**Step 6: Create `templates/admin_panel/tours/partials/itinerary_tab.html`** (full)

```html
{% load tz %}
<div id="itinerary-builder">
  <div class="d-flex align-items-center mb-3">
    <span class="text-muted small flex-grow-1">Drag rows to reorder within a day.</span>
    <button class="btn btn-sm btn-warning fw-bold"
            hx-get="{% url 'dashboard:itinerary_add' tour.pk %}"
            hx-target="#itinerary-form-slot"
            hx-swap="innerHTML">
      <i class="bi bi-plus-lg me-1"></i>Add Activity
    </button>
  </div>

  <div id="itinerary-form-slot" class="mb-3"></div>

  {% if items_by_day %}
    {% for day, items in items_by_day.items %}
    <div class="mb-3">
      <div class="fw-bold small text-muted mb-2 text-uppercase" style="letter-spacing:.5px;">Day {{ day }}</div>
      <div id="day-{{ day }}-list"
           x-data="sortable('day-{{ day }}-list', {{ tour.pk }})"
           @sortend="saveOrder($event)">
        {% for item in items %}
          {% include 'admin_panel/tours/partials/itinerary_item_row.html' with item=item only %}
        {% endfor %}
      </div>
    </div>
    {% endfor %}
  {% else %}
    <div class="text-center text-muted py-4">
      <i class="bi bi-list-check fs-2 d-block mb-2 opacity-25"></i>
      <p>No activities yet. Add your first one above.</p>
    </div>
  {% endif %}
</div>

<script>
function sortable(listId, tourPk) {
  return {
    init() {
      // Simple Alpine.js sortable using drag events (no library dependency)
      const list = document.getElementById(listId);
      let dragging = null;

      list.addEventListener('dragstart', e => {
        dragging = e.target.closest('.itinerary-row');
        dragging.style.opacity = '0.5';
      });
      list.addEventListener('dragend', e => {
        if (dragging) dragging.style.opacity = '';
        dragging = null;
        this.saveOrder(list, tourPk);
      });
      list.addEventListener('dragover', e => {
        e.preventDefault();
        const row = e.target.closest('.itinerary-row');
        if (row && dragging && row !== dragging) {
          const rect = row.getBoundingClientRect();
          const mid = rect.top + rect.height / 2;
          if (e.clientY < mid) list.insertBefore(dragging, row);
          else list.insertBefore(dragging, row.nextSibling);
        }
      });
    },
    saveOrder(list, tourPk) {
      const rows = list.querySelectorAll('.itinerary-row[data-item-id]');
      const payload = Array.from(rows).map((row, idx) => ({
        id: parseInt(row.dataset.itemId), order: idx
      }));
      fetch(`/guide/tours/${tourPk}/itinerary/reorder/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '',
        },
        body: JSON.stringify(payload),
      });
    },
  };
}
</script>
```

---

**Step 7: Create `templates/admin_panel/tours/partials/itinerary_item_row.html`**

```html
<div class="itinerary-row" draggable="true" data-item-id="{{ item.pk }}" id="item-{{ item.pk }}">
  <span class="drag-handle"><i class="bi bi-grip-vertical"></i></span>
  <div class="flex-grow-1 min-width-0">
    <div class="fw-semibold text-truncate" style="font-size:14px;">{{ item.title }}</div>
    <div class="text-muted" style="font-size:11px;">
      {{ item.start_time|time:"H:i" }} · {{ item.duration_display }}
      {% if item.category %}
        <span class="badge rounded-pill ms-1" style="background:{{ item.category.colour }};font-size:10px;">
          {{ item.category.name }}
        </span>
      {% endif %}
    </div>
  </div>
  <div class="d-flex gap-1 flex-shrink-0">
    <button class="btn btn-sm btn-link text-warning p-1"
            hx-get="{% url 'dashboard:itinerary_edit' tour.pk item.pk %}"
            hx-target="#itinerary-form-slot"
            hx-swap="innerHTML">
      <i class="bi bi-pencil"></i>
    </button>
    <button class="btn btn-sm btn-link text-danger p-1"
            hx-delete="{% url 'dashboard:itinerary_delete' tour.pk item.pk %}"
            hx-confirm="Delete '{{ item.title|escapejs }}'?"
            hx-target="#item-{{ item.pk }}"
            hx-swap="outerHTML swap:0.2s">
      <i class="bi bi-trash"></i>
    </button>
  </div>
</div>
```

---

**Step 8: Create `templates/admin_panel/tours/partials/itinerary_item_form.html`**

```html
<div class="inline-form-card" id="itinerary-inline-form">
  <div class="d-flex align-items-center mb-3">
    <span class="fw-bold small flex-grow-1">
      {% if item %}Edit Activity{% else %}New Activity{% endif %}
    </span>
    <button type="button" class="btn btn-sm btn-link text-muted"
            hx-get="" hx-target="#itinerary-form-slot" hx-swap="innerHTML">
      <i class="bi bi-x-lg"></i>
    </button>
  </div>
  <form method="post"
        hx-post="{% if item %}{% url 'dashboard:itinerary_edit' tour.pk item.pk %}{% else %}{% url 'dashboard:itinerary_add' tour.pk %}{% endif %}"
        hx-target="#itinerary-form-slot"
        hx-swap="innerHTML"
        novalidate>
    {% csrf_token %}
    {% for field in form %}
      {% if not field.is_hidden %}
      <div class="mb-2">
        <label class="form-label small fw-semibold mb-1" for="{{ field.id_for_label }}">{{ field.label }}</label>
        {{ field }}
        {% if field.errors %}
          <div class="text-danger" style="font-size:11px;">{{ field.errors.0 }}</div>
        {% endif %}
      </div>
      {% else %}
        {{ field }}
      {% endif %}
    {% endfor %}
    <div class="d-flex gap-2 mt-3">
      <button type="submit" class="btn btn-sm btn-warning fw-bold flex-fill">
        {% if item %}Save{% else %}Add Activity{% endif %}
      </button>
    </div>
  </form>
</div>
<script>
document.querySelectorAll('#itinerary-inline-form input:not([type=checkbox]):not([type=hidden]), #itinerary-inline-form select, #itinerary-inline-form textarea').forEach(el => {
  el.classList.add(el.tagName === 'SELECT' ? 'form-select' : 'form-control');
  el.classList.add('form-control-sm');
});
</script>
```

---

**Step 9: Run tests — expect PASS**

```bash
.venv/Scripts/python manage.py test dashboard -v 2
```

---

**Step 10: Commit**

```bash
git add dashboard/ templates/admin_panel/tours/
git commit -m "feat: itinerary builder - add/edit/delete/reorder activities per tour"
```

---

## Task 28: Guest Manifest Tab

**Files:**
- Modify: `dashboard/views.py` — tour_detail already passes bookings; no new views needed
- Create: `templates/admin_panel/tours/partials/guests_tab.html` (full)
- Test: `dashboard/tests.py`

---

**Step 1: Write failing tests**

```python
from apps.bookings.models import Booking


class GuestManifestTest(TestCase):
    def setUp(self):
        self.guide = make_user('guide@guests.com', UserProfile.Role.GUIDE)
        self.client.force_login(self.guide)
        self.tour = make_tour(self.guide)

    def test_guests_tab_shows_enrolled_guests(self):
        guest = make_user('guest@guests.com', UserProfile.Role.GUEST)
        guest.profile.first_name = 'Alice'
        guest.profile.last_name = 'Botha'
        guest.profile.save()
        Booking.objects.create(tour=self.tour, user=guest, status=Booking.Status.CONFIRMED)
        resp = self.client.get(
            reverse('dashboard:tour_detail', args=[self.tour.pk]),
            {'tab': 'guests'}
        )
        self.assertContains(resp, 'Alice')

    def test_guests_tab_shows_empty_state(self):
        resp = self.client.get(
            reverse('dashboard:tour_detail', args=[self.tour.pk]),
            {'tab': 'guests'}
        )
        self.assertContains(resp, 'No guests')

    def test_guests_tab_shows_rsvp_status_badge(self):
        guest = make_user('rsvp@guests.com', UserProfile.Role.GUEST)
        Booking.objects.create(tour=self.tour, user=guest, status=Booking.Status.RSVP_PENDING)
        resp = self.client.get(
            reverse('dashboard:tour_detail', args=[self.tour.pk]),
            {'tab': 'guests'}
        )
        self.assertContains(resp, 'RSVP')

    def test_guests_shows_dietary_info_for_guide(self):
        guest = make_user('diet@guests.com', UserProfile.Role.GUEST)
        guest.profile.dietary_requirements = 'Vegan'
        guest.profile.save()
        Booking.objects.create(tour=self.tour, user=guest, status=Booking.Status.CONFIRMED)
        resp = self.client.get(
            reverse('dashboard:tour_detail', args=[self.tour.pk]),
            {'tab': 'guests'}
        )
        self.assertContains(resp, 'Vegan')
```

**Step 2: Run — expect FAIL**

```bash
.venv/Scripts/python manage.py test dashboard.GuestManifestTest -v 2
```

---

**Step 3: Create `templates/admin_panel/tours/partials/guests_tab.html`** (full)

```html
<div class="d-flex align-items-center mb-3">
  <span class="text-muted small flex-grow-1">{{ bookings.count }} enrolled</span>
</div>

{% for booking in bookings %}
<div class="guest-row">
  <div class="guest-avatar">
    {{ booking.user.profile.initials|upper }}
  </div>
  <div class="flex-grow-1 min-width-0">
    <div class="fw-semibold text-truncate" style="font-size:14px;">
      {{ booking.user.profile.full_name }}
    </div>
    <div class="text-muted" style="font-size:11px;">{{ booking.user.email }}</div>
    {% if booking.user.profile.dietary_requirements %}
    <div class="text-muted" style="font-size:11px;">
      <i class="bi bi-egg-fried me-1"></i>{{ booking.user.profile.dietary_requirements }}
    </div>
    {% endif %}
    {% if booking.user.profile.medical_conditions %}
    <div class="text-warning" style="font-size:11px;">
      <i class="bi bi-heart-pulse me-1"></i>{{ booking.user.profile.medical_conditions }}
    </div>
    {% endif %}
  </div>
  <div class="flex-shrink-0">
    <span class="badge rounded-pill
      {% if booking.status == 'CONFIRMED' %}bg-success
      {% elif booking.status == 'RSVP_PENDING' %}bg-warning text-dark
      {% elif booking.status == 'INVITED' %}bg-secondary
      {% else %}bg-danger{% endif %}
    " style="font-size:10px;">
      {{ booking.get_status_display }}
    </span>
    {% if booking.user.profile.phone_whatsapp %}
    <a href="https://wa.me/{{ booking.user.profile.phone_whatsapp|cut:'+' }}"
       class="btn btn-sm btn-link text-success p-1 ms-1"
       target="_blank" rel="noopener">
      <i class="bi bi-whatsapp"></i>
    </a>
    {% endif %}
  </div>
</div>
{% empty %}
<div class="text-center text-muted py-4">
  <i class="bi bi-people fs-2 d-block mb-2 opacity-25"></i>
  <p>No guests enrolled yet.</p>
</div>
{% endfor %}
```

**Step 4: Run tests — expect PASS**

```bash
.venv/Scripts/python manage.py test dashboard -v 2
```

**Step 5: Commit**

```bash
git add templates/admin_panel/tours/partials/guests_tab.html
git commit -m "feat: guest manifest tab with dietary, medical, WhatsApp links, status badges"
```

---

## Task 29: Activity Library Tab

**Files:**
- Modify: `dashboard/views.py` — activities_list, activity_create, activity_edit, activity_delete
- Modify: `dashboard/forms.py` — ActivityCategoryForm
- Modify: `dashboard/urls.py` — activity CRUD URLs
- Create: `templates/admin_panel/activities/list.html` (full)
- Create: `templates/admin_panel/activities/partials/category_form.html`
- Test: `dashboard/tests.py`

---

**Step 1: Write failing tests**

```python
from apps.tours.models import ActivityCategory


class ActivityLibraryTest(TestCase):
    def setUp(self):
        self.guide = make_user('guide@activities.com', UserProfile.Role.GUIDE)
        self.client.force_login(self.guide)

    def test_activities_list_shows_categories(self):
        ActivityCategory.objects.create(name='Hiking', icon='geo-alt', colour='#198754')
        resp = self.client.get(reverse('dashboard:activities_list'))
        self.assertContains(resp, 'Hiking')

    def test_create_category_post(self):
        resp = self.client.post(reverse('dashboard:activity_create'), {
            'name': 'Snorkelling',
            'icon': 'water',
            'colour': '#0d6efd',
            'is_active': True,
            'order': 0,
        })
        self.assertTrue(ActivityCategory.objects.filter(name='Snorkelling').exists())

    def test_delete_category(self):
        cat = ActivityCategory.objects.create(name='Wine Tasting', icon='cup', colour='#6f42c1')
        resp = self.client.delete(reverse('dashboard:activity_delete', args=[cat.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(ActivityCategory.objects.filter(pk=cat.pk).exists())

    def test_edit_category_updates_name(self):
        cat = ActivityCategory.objects.create(name='Old Cat', icon='star', colour='#F97316')
        self.client.post(reverse('dashboard:activity_edit', args=[cat.pk]), {
            'name': 'New Cat', 'icon': 'star', 'colour': '#F97316', 'is_active': True, 'order': 0,
        })
        cat.refresh_from_db()
        self.assertEqual(cat.name, 'New Cat')
```

**Step 2: Run — expect FAIL**

```bash
.venv/Scripts/python manage.py test dashboard.ActivityLibraryTest -v 2
```

---

**Step 3: Add `ActivityCategoryForm` to `dashboard/forms.py`**

```python
from apps.tours.models import ActivityCategory


class ActivityCategoryForm(forms.ModelForm):
    class Meta:
        model = ActivityCategory
        fields = ['name', 'icon', 'colour', 'is_active', 'order']
        widgets = {
            'colour': forms.TextInput(attrs={'type': 'color'}),
        }
```

---

**Step 4: Add activity URLs to `dashboard/urls.py`**

```python
path('activities/create/', views.activity_create, name='activity_create'),
path('activities/<int:pk>/edit/', views.activity_edit, name='activity_edit'),
path('activities/<int:pk>/delete/', views.activity_delete, name='activity_delete'),
```

---

**Step 5: Add activity views to `dashboard/views.py`**

```python
from apps.tours.models import ActivityCategory
from .forms import TourForm, ItineraryItemForm, ActivityCategoryForm


@guide_required
def activities_list(request):
    categories = ActivityCategory.objects.order_by('order', 'name')
    return render(request, 'admin_panel/activities/list.html', {
        'categories': categories,
        'dev_mode': _dev_mode(),
    })


@guide_required
def activity_create(request):
    if request.method == 'POST':
        form = ActivityCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                categories = ActivityCategory.objects.order_by('order', 'name')
                return render(request, 'admin_panel/activities/list.html',
                              {'categories': categories, 'dev_mode': _dev_mode()})
            return redirect('dashboard:activities_list')
    else:
        form = ActivityCategoryForm()
    return render(request, 'admin_panel/activities/partials/category_form.html', {
        'form': form, 'dev_mode': _dev_mode(),
    })


@guide_required
def activity_edit(request, pk):
    from django.shortcuts import get_object_or_404
    cat = get_object_or_404(ActivityCategory, pk=pk)
    if request.method == 'POST':
        form = ActivityCategoryForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            return redirect('dashboard:activities_list')
    else:
        form = ActivityCategoryForm(instance=cat)
    return render(request, 'admin_panel/activities/partials/category_form.html', {
        'form': form, 'category': cat, 'dev_mode': _dev_mode(),
    })


@guide_required
def activity_delete(request, pk):
    from django.shortcuts import get_object_or_404
    from django.http import HttpResponse
    cat = get_object_or_404(ActivityCategory, pk=pk)
    if request.method in ('POST', 'DELETE'):
        cat.delete()
        return HttpResponse('')
    return HttpResponse(status=405)
```

---

**Step 6: Create `templates/admin_panel/activities/list.html`**

```html
{% extends 'admin_panel/base.html' %}
{% block title %}Activity Library{% endblock %}
{% block tab_activities %}active{% endblock %}

{% block content %}
<div class="d-flex align-items-center mb-3">
  <h6 class="mb-0 fw-bold flex-grow-1">Activity Library</h6>
  <a href="{% url 'dashboard:activity_create' %}" class="btn btn-sm btn-warning fw-bold">
    <i class="bi bi-plus-lg me-1"></i>New Category
  </a>
</div>

<p class="text-muted small mb-3">
  Activity categories group your itinerary items. Assign colour-coded categories when building tours.
</p>

{% for cat in categories %}
<div class="tour-card" id="cat-{{ cat.pk }}">
  <div class="d-flex align-items-center">
    <span class="rounded-circle me-3 d-flex align-items-center justify-content-center"
          style="width:36px;height:36px;background:{{ cat.colour }};flex-shrink:0;">
      <i class="bi bi-{{ cat.icon }} text-white"></i>
    </span>
    <div class="flex-grow-1">
      <div class="fw-semibold">{{ cat.name }}</div>
      <div class="text-muted" style="font-size:11px;">
        {{ cat.itinerary_items.count }} items
        {% if not cat.is_active %}<span class="badge bg-secondary ms-1">Hidden</span>{% endif %}
      </div>
    </div>
    <div class="d-flex gap-1">
      <a href="{% url 'dashboard:activity_edit' cat.pk %}" class="btn btn-sm btn-link text-warning p-1">
        <i class="bi bi-pencil"></i>
      </a>
      <button class="btn btn-sm btn-link text-danger p-1"
              hx-delete="{% url 'dashboard:activity_delete' cat.pk %}"
              hx-confirm="Delete {{ cat.name }}?"
              hx-target="#cat-{{ cat.pk }}"
              hx-swap="outerHTML swap:0.2s">
        <i class="bi bi-trash"></i>
      </button>
    </div>
  </div>
</div>
{% empty %}
<div class="text-center text-muted py-5">
  <i class="bi bi-lightning fs-2 d-block mb-2 opacity-25"></i>
  <p>No activity categories yet.</p>
  <a href="{% url 'dashboard:activity_create' %}" class="btn btn-warning">Add First Category</a>
</div>
{% endfor %}
{% endblock %}
```

---

**Step 7: Create `templates/admin_panel/activities/partials/category_form.html`**

```html
{% extends 'admin_panel/base.html' %}
{% block title %}{% if category %}Edit{% else %}New{% endif %} Category{% endblock %}
{% block tab_activities %}active{% endblock %}

{% block content %}
<div class="d-flex align-items-center mb-3">
  <a href="{% url 'dashboard:activities_list' %}" class="btn btn-sm btn-link ps-0 text-muted">
    <i class="bi bi-arrow-left me-1"></i>Back
  </a>
  <h6 class="mb-0 fw-bold flex-grow-1">
    {% if category %}Edit Category{% else %}New Category{% endif %}
  </h6>
</div>

<div class="inline-form-card">
  <form method="post" novalidate>
    {% csrf_token %}
    {% for field in form %}
    <div class="mb-3">
      <label class="form-label small fw-bold">{{ field.label }}</label>
      {{ field }}
      {% if field.errors %}<div class="text-danger small">{{ field.errors.0 }}</div>{% endif %}
    </div>
    {% endfor %}
    <p class="text-muted" style="font-size:11px;">
      <strong>Icon:</strong> Use any Bootstrap Icons name (e.g. <code>geo-alt</code>, <code>water</code>, <code>bicycle</code>).
      Find all at <em>icons.getbootstrap.com</em>
    </p>
    <button type="submit" class="btn btn-warning fw-bold w-100 mt-2">
      {% if category %}Save Changes{% else %}Create Category{% endif %}
    </button>
  </form>
</div>
{% endblock %}

{% block extra_js %}
<script>
document.querySelectorAll('input:not([type=checkbox]):not([type=color]), select, textarea').forEach(el => {
  el.classList.add(el.tagName === 'SELECT' ? 'form-select' : 'form-control');
});
document.querySelectorAll('input[type=checkbox]').forEach(el => el.classList.add('form-check-input'));
</script>
{% endblock %}
```

**Step 8: Run tests — expect PASS**

```bash
.venv/Scripts/python manage.py test dashboard -v 2
```

**Step 9: Commit**

```bash
git add dashboard/ templates/admin_panel/activities/
git commit -m "feat: activity library tab - category CRUD with colour picker and icon field"
```

---

## Task 30: Guides Tab

**Files:**
- Modify: `dashboard/views.py` — guides_list, guide_edit
- Modify: `dashboard/urls.py` — guide URLs
- Create: `templates/admin_panel/guides/list.html` (full)
- Create: `templates/admin_panel/guides/partials/guide_form.html`
- Test: `dashboard/tests.py`

---

**Step 1: Write failing tests**

```python
class GuidesTabTest(TestCase):
    def setUp(self):
        self.admin = make_user('admin@guides.com', is_staff=True)
        self.client.force_login(self.admin)

    def test_guides_list_shows_guide_users(self):
        guide = make_user('g1@guides.com', UserProfile.Role.GUIDE)
        guide.profile.first_name = 'Bob'
        guide.profile.save()
        resp = self.client.get(reverse('dashboard:guides_list'))
        self.assertContains(resp, 'Bob')

    def test_guides_list_excludes_guests(self):
        make_user('guest@guides.com', UserProfile.Role.GUEST)
        resp = self.client.get(reverse('dashboard:guides_list'))
        self.assertNotContains(resp, 'guest@guides.com')

    def test_edit_guide_role(self):
        guide = make_user('edit@guides.com', UserProfile.Role.GUIDE)
        resp = self.client.post(
            reverse('dashboard:guide_edit', args=[guide.profile.pk]),
            {'role': 'OPERATOR'}
        )
        guide.profile.refresh_from_db()
        self.assertEqual(guide.profile.role, 'OPERATOR')

    def test_non_staff_cannot_access_guides_tab(self):
        """Regular guides cannot manage other guides."""
        guide = make_user('regularguide@test.com', UserProfile.Role.GUIDE)
        self.client.force_login(guide)
        resp = self.client.get(reverse('dashboard:guides_list'))
        self.assertEqual(resp.status_code, 403)
```

**Step 2: Run — expect FAIL**

```bash
.venv/Scripts/python manage.py test dashboard.GuidesTabTest -v 2
```

---

**Step 3: Add `GuideRoleForm` to `dashboard/forms.py`**

```python
from apps.accounts.models import UserProfile


class GuideRoleForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['role', 'first_name', 'last_name', 'phone_whatsapp']
        widgets = {
            'role': forms.Select(choices=UserProfile.Role.choices),
        }
```

---

**Step 4: Add guide URLs to `dashboard/urls.py`**

```python
path('guides/<int:pk>/edit/', views.guide_edit, name='guide_edit'),
```

---

**Step 5: Update views in `dashboard/views.py`**

Add a new decorator for staff-only access:

```python
def staff_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapped
```

Update guides views:

```python
from apps.accounts.models import UserProfile as Profile
from .forms import TourForm, ItineraryItemForm, ActivityCategoryForm, GuideRoleForm


@guide_required
def guides_list(request):
    if not request.user.is_staff:
        raise PermissionDenied
    GUIDE_ROLES = ['GUIDE', 'OPERATOR', 'ADMIN']
    profiles = (
        Profile.objects
        .filter(role__in=GUIDE_ROLES)
        .select_related('user')
        .order_by('role', 'last_name', 'first_name')
    )
    return render(request, 'admin_panel/guides/list.html', {
        'profiles': profiles,
        'dev_mode': _dev_mode(),
    })


@staff_required
def guide_edit(request, pk):
    from django.shortcuts import get_object_or_404
    profile = get_object_or_404(Profile, pk=pk)
    if request.method == 'POST':
        form = GuideRoleForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('dashboard:guides_list')
    else:
        form = GuideRoleForm(instance=profile)
    return render(request, 'admin_panel/guides/partials/guide_form.html', {
        'form': form, 'profile': profile, 'dev_mode': _dev_mode(),
    })
```

---

**Step 6: Create `templates/admin_panel/guides/list.html`**

```html
{% extends 'admin_panel/base.html' %}
{% block title %}Guides{% endblock %}
{% block tab_guides %}active{% endblock %}

{% block content %}
<h6 class="fw-bold mb-3">Guide & Operator Accounts</h6>

{% for profile in profiles %}
<div class="guest-row">
  <div class="guest-avatar" style="background:#1a3a2a;">
    {{ profile.initials|upper }}
  </div>
  <div class="flex-grow-1">
    <div class="fw-semibold" style="font-size:14px;">{{ profile.full_name }}</div>
    <div class="text-muted" style="font-size:11px;">{{ profile.user.email }}</div>
  </div>
  <div class="d-flex align-items-center gap-2">
    <span class="badge bg-secondary rounded-pill" style="font-size:10px;">
      {{ profile.get_role_display }}
    </span>
    <a href="{% url 'dashboard:guide_edit' profile.pk %}" class="btn btn-sm btn-link text-warning p-1">
      <i class="bi bi-pencil"></i>
    </a>
  </div>
</div>
{% empty %}
<div class="text-center text-muted py-5">
  <i class="bi bi-person-badge fs-2 d-block mb-2 opacity-25"></i>
  <p>No guides yet. Assign the Guide role to a user via Django admin.</p>
</div>
{% endfor %}
{% endblock %}
```

---

**Step 7: Create `templates/admin_panel/guides/partials/guide_form.html`**

```html
{% extends 'admin_panel/base.html' %}
{% block title %}Edit Guide{% endblock %}
{% block tab_guides %}active{% endblock %}

{% block content %}
<div class="d-flex align-items-center mb-3">
  <a href="{% url 'dashboard:guides_list' %}" class="btn btn-sm btn-link ps-0 text-muted">
    <i class="bi bi-arrow-left me-1"></i>Back
  </a>
  <h6 class="mb-0 fw-bold flex-grow-1">Edit {{ profile.full_name }}</h6>
</div>

<div class="inline-form-card">
  <form method="post" novalidate>
    {% csrf_token %}
    {% for field in form %}
    <div class="mb-3">
      <label class="form-label small fw-bold">{{ field.label }}</label>
      {{ field }}
      {% if field.errors %}<div class="text-danger small">{{ field.errors.0 }}</div>{% endif %}
    </div>
    {% endfor %}
    <button type="submit" class="btn btn-warning fw-bold w-100 mt-2">Save Changes</button>
  </form>
</div>
{% endblock %}

{% block extra_js %}
<script>
document.querySelectorAll('input:not([type=checkbox]), select, textarea').forEach(el => {
  el.classList.add(el.tagName === 'SELECT' ? 'form-select' : 'form-control');
});
document.querySelectorAll('input[type=checkbox]').forEach(el => el.classList.add('form-check-input'));
</script>
{% endblock %}
```

**Step 8: Run tests — expect PASS**

```bash
.venv/Scripts/python manage.py test dashboard -v 2
```

**Step 9: Commit**

```bash
git add dashboard/ templates/admin_panel/guides/
git commit -m "feat: guides tab - list and edit guide/operator roles (staff-only)"
```

---

## Task 31: QR Code Generation

**Files:**
- Modify: `dashboard/views.py` — tour_qr (full)
- Create: `templates/admin_panel/tours/qr.html`
- Test: `dashboard/tests.py`

**Prerequisite:** Install `qrcode[pil]` if not already installed.

---

**Step 1: Install qrcode**

```bash
.venv/Scripts/pip install "qrcode[pil]"
```

Add to `requirements.txt`:
```
qrcode[pil]>=7.4
```

---

**Step 2: Write failing tests**

```python
class QRCodeTest(TestCase):
    def setUp(self):
        self.guide = make_user('guide@qr.com', UserProfile.Role.GUIDE)
        self.client.force_login(self.guide)
        self.tour = make_tour(self.guide, 'QR Tour')

    def test_qr_page_returns_200(self):
        resp = self.client.get(reverse('dashboard:tour_qr', args=[self.tour.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_qr_page_contains_tour_code(self):
        resp = self.client.get(reverse('dashboard:tour_qr', args=[self.tour.pk]))
        self.assertContains(resp, self.tour.tour_code)

    def test_qr_png_endpoint_returns_image(self):
        resp = self.client.get(reverse('dashboard:tour_qr_png', args=[self.tour.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'image/png')
```

**Step 3: Run — expect FAIL**

```bash
.venv/Scripts/python manage.py test dashboard.QRCodeTest -v 2
```

---

**Step 4: Add QR PNG URL to `dashboard/urls.py`**

```python
path('tours/<int:pk>/qr.png', views.tour_qr_png, name='tour_qr_png'),
```

---

**Step 5: Update `dashboard/views.py` — tour_qr + tour_qr_png**

```python
@guide_required
def tour_qr(request, pk):
    from django.shortcuts import get_object_or_404
    tour = get_object_or_404(Tour, pk=pk)
    join_url = request.build_absolute_uri(f'/app/join/lookup/')
    return render(request, 'admin_panel/tours/qr.html', {
        'tour': tour,
        'join_url': join_url,
        'qr_url': reverse('dashboard:tour_qr_png', args=[pk]),
        'dev_mode': _dev_mode(),
    })


@guide_required
def tour_qr_png(request, pk):
    import qrcode
    import io
    from django.http import HttpResponse
    from django.shortcuts import get_object_or_404
    tour = get_object_or_404(Tour, pk=pk)
    join_url = request.build_absolute_uri(f'/app/join/lookup/?code={tour.tour_code}')
    qr = qrcode.QRCode(box_size=8, border=3)
    qr.add_data(join_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#1a3a2a', back_color='white')
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    return HttpResponse(buf.read(), content_type='image/png')
```

---

**Step 6: Create `templates/admin_panel/tours/qr.html`**

```html
{% extends 'admin_panel/base.html' %}
{% block title %}QR Code — {{ tour.name }}{% endblock %}
{% block tab_tours %}active{% endblock %}

{% block content %}
<div class="d-flex align-items-center mb-3">
  <a href="{% url 'dashboard:tour_detail' tour.pk %}" class="btn btn-sm btn-link ps-0 text-muted">
    <i class="bi bi-arrow-left me-1"></i>Back to Tour
  </a>
  <h6 class="mb-0 fw-bold flex-grow-1">Join QR Code</h6>
</div>

<div class="qr-container mb-3">
  <img src="{% url 'dashboard:tour_qr_png' tour.pk %}"
       alt="QR Code for {{ tour.name }}"
       class="img-fluid mb-3"
       style="max-width:240px;">

  <div class="fw-bold font-monospace fs-4 mb-1">{{ tour.tour_code }}</div>
  <div class="text-muted small">Guests scan to join — or enter the code manually</div>
</div>

<div class="d-flex gap-2">
  <a href="{% url 'dashboard:tour_qr_png' tour.pk %}"
     download="{{ tour.tour_code }}-qr.png"
     class="btn btn-warning fw-bold flex-fill">
    <i class="bi bi-download me-1"></i>Download PNG
  </a>
  <button class="btn btn-outline-secondary"
          onclick="navigator.share ? navigator.share({title:'{{ tour.name|escapejs }}', url:'{{ join_url|escapejs }}'}) : navigator.clipboard.writeText('{{ join_url|escapejs }}').then(() => alert('URL copied!'))">
    <i class="bi bi-share"></i>
  </button>
</div>
{% endblock %}
```

**Step 7: Run tests — expect PASS**

```bash
.venv/Scripts/python manage.py test dashboard -v 2
```

**Step 8: Commit**

```bash
git add dashboard/ templates/admin_panel/tours/qr.html requirements.txt
git commit -m "feat: QR code generation per tour - PNG endpoint + shareable/downloadable view"
```

---

## Task 32: Photo Gallery

**Files:**
- Modify: `dashboard/models.py` — TourPhoto model
- Create: `dashboard/migrations/0001_initial.py` (run makemigrations)
- Modify: `dashboard/urls.py` — photo gallery URLs
- Modify: `dashboard/views.py` — photos_list, photo_upload, photo_delete
- Create: `templates/admin_panel/tours/partials/photos_tab.html`
- Test: `dashboard/tests.py`

---

**Step 1: Write failing tests**

```python
from django.core.files.uploadedfile import SimpleUploadedFile
import tempfile, os


class PhotoGalleryTest(TestCase):
    def setUp(self):
        self.guide = make_user('guide@photos.com', UserProfile.Role.GUIDE)
        self.client.force_login(self.guide)
        self.tour = make_tour(self.guide)

    def test_photo_upload_creates_record(self):
        from dashboard.models import TourPhoto
        img = SimpleUploadedFile('test.jpg', b'\xff\xd8\xff\xe0' + b'\x00' * 100, content_type='image/jpeg')
        resp = self.client.post(
            reverse('dashboard:photo_upload', args=[self.tour.pk]),
            {'photo': img},
        )
        self.assertEqual(TourPhoto.objects.filter(tour=self.tour).count(), 1)

    def test_photo_delete_removes_record(self):
        from dashboard.models import TourPhoto
        photo = TourPhoto.objects.create(
            tour=self.tour,
            uploaded_by=self.guide,
            photo=SimpleUploadedFile('del.jpg', b'\xff\xd8\xff\xe0' + b'\x00'*100, content_type='image/jpeg'),
        )
        resp = self.client.delete(reverse('dashboard:photo_delete', args=[photo.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(TourPhoto.objects.filter(pk=photo.pk).exists())

    def test_photos_tab_shows_photos_count(self):
        resp = self.client.get(
            reverse('dashboard:tour_detail', args=[self.tour.pk]),
            {'tab': 'photos'}
        )
        self.assertEqual(resp.status_code, 200)
```

**Step 2: Run — expect FAIL**

```bash
.venv/Scripts/python manage.py test dashboard.PhotoGalleryTest -v 2
```

---

**Step 3: Add `TourPhoto` model to `dashboard/models.py`**

```python
from django.db import models
from django.contrib.auth import get_user_model
from apps.tours.models import Tour

User = get_user_model()


class TourPhoto(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='photos')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_photos')
    photo = models.ImageField(upload_to='tour_photos/%Y/%m/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'Photo for {self.tour} ({self.uploaded_at.date()})'
```

**Step 4: Create and run migration**

```bash
.venv/Scripts/python manage.py makemigrations dashboard
.venv/Scripts/python manage.py migrate
```

---

**Step 5: Add photo URLs to `dashboard/urls.py`**

```python
path('tours/<int:tour_pk>/photos/', views.photos_list, name='photos_list'),
path('tours/<int:tour_pk>/photos/upload/', views.photo_upload, name='photo_upload'),
path('photos/<int:pk>/delete/', views.photo_delete, name='photo_delete'),
```

---

**Step 6: Add photo views to `dashboard/views.py`**

```python
from dashboard.models import TourPhoto


@guide_required
def photos_list(request, tour_pk):
    tour = _get_tour_for_guide(request, tour_pk)
    photos = TourPhoto.objects.filter(tour=tour)
    return render(request, 'admin_panel/tours/partials/photos_tab.html', {
        'tour': tour, 'photos': photos, 'dev_mode': _dev_mode(),
    })


@guide_required
def photo_upload(request, tour_pk):
    from django.http import HttpResponse
    tour = _get_tour_for_guide(request, tour_pk)
    if request.method == 'POST' and request.FILES.get('photo'):
        photo = TourPhoto.objects.create(
            tour=tour,
            uploaded_by=request.user,
            photo=request.FILES['photo'],
            caption=request.POST.get('caption', ''),
        )
        if request.headers.get('HX-Request'):
            return render(request, 'admin_panel/tours/partials/photo_thumb.html', {'photo': photo})
        return redirect(f"{reverse('dashboard:tour_detail', args=[tour_pk])}?tab=photos")
    return HttpResponse(status=400)


@guide_required
def photo_delete(request, pk):
    from django.shortcuts import get_object_or_404
    from django.http import HttpResponse
    photo = get_object_or_404(TourPhoto, pk=pk)
    _get_tour_for_guide(request, photo.tour_id)  # enforce ownership
    if request.method in ('POST', 'DELETE'):
        if photo.photo and hasattr(photo.photo, 'path'):
            import os
            try:
                os.remove(photo.photo.path)
            except FileNotFoundError:
                pass
        photo.delete()
        return HttpResponse('')
    return HttpResponse(status=405)
```

---

**Step 7: Update tour_detail to handle photos tab**

In `dashboard/views.py` — update tour_detail to include photos:

```python
@guide_required
def tour_detail(request, pk):
    # ... existing code ...
    from dashboard.models import TourPhoto
    photos = TourPhoto.objects.filter(tour=tour)
    active_tab = request.GET.get('tab', 'itinerary')

    return render(request, 'admin_panel/tours/detail.html', {
        'tour': tour,
        'active_tab': active_tab,
        'bookings': bookings,
        'items_by_day': items_by_day,
        'photos': photos,
        'dev_mode': _dev_mode(),
    })
```

---

**Step 8: Update `templates/admin_panel/tours/detail.html`** to add Photos sub-tab

Add to the `<ul class="nav nav-tabs">` block:

```html
<li class="nav-item">
  <a class="nav-link {% if active_tab == 'photos' %}active{% endif %}" href="?tab=photos">
    Photos
    {% if photos %}<span class="badge bg-secondary ms-1">{{ photos.count }}</span>{% endif %}
  </a>
</li>
```

Add to the tab content block:

```html
{% elif active_tab == 'photos' %}
  {% include 'admin_panel/tours/partials/photos_tab.html' %}
```

---

**Step 9: Create `templates/admin_panel/tours/partials/photos_tab.html`**

```html
<div class="d-flex align-items-center mb-3">
  <span class="text-muted small flex-grow-1">{{ photos.count }} photos</span>
  <label class="btn btn-sm btn-warning fw-bold" for="photo-upload-input">
    <i class="bi bi-camera me-1"></i>Upload
    <input id="photo-upload-input" type="file" accept="image/*" multiple style="display:none;"
           hx-post="{% url 'dashboard:photo_upload' tour.pk %}"
           hx-encoding="multipart/form-data"
           hx-target="#photo-grid"
           hx-swap="afterbegin"
           name="photo">
  </label>
</div>

<div class="photo-grid" id="photo-grid">
  {% for photo in photos %}
  <div id="photo-{{ photo.pk }}" style="position:relative;">
    <img src="{{ photo.photo.url }}" alt="{{ photo.caption }}" class="photo-thumb"
         data-bs-toggle="modal" data-bs-target="#lightbox" data-src="{{ photo.photo.url }}">
    <button class="btn btn-sm btn-danger"
            style="position:absolute;top:4px;right:4px;padding:2px 6px;"
            hx-delete="{% url 'dashboard:photo_delete' photo.pk %}"
            hx-confirm="Delete this photo?"
            hx-target="#photo-{{ photo.pk }}"
            hx-swap="outerHTML">
      <i class="bi bi-x"></i>
    </button>
  </div>
  {% empty %}
  <div class="col-12 text-center text-muted py-4" id="empty-photos">
    <i class="bi bi-camera fs-2 d-block mb-2 opacity-25"></i>
    <p>No photos yet. Upload some!</p>
  </div>
  {% endfor %}
</div>

<!-- Lightbox modal -->
<div class="modal fade" id="lightbox" tabindex="-1">
  <div class="modal-dialog modal-fullscreen-sm-down modal-lg modal-dialog-centered">
    <div class="modal-content bg-dark">
      <div class="modal-header border-0">
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body text-center p-2">
        <img id="lightbox-img" src="" alt="Photo" class="img-fluid rounded">
      </div>
    </div>
  </div>
</div>

<script>
document.getElementById('photo-grid').addEventListener('click', e => {
  const img = e.target.closest('[data-src]');
  if (img) document.getElementById('lightbox-img').src = img.dataset.src;
});
</script>
```

**Step 10: Run all tests — expect PASS**

```bash
.venv/Scripts/python manage.py test dashboard -v 2
```

---

**Step 11: Run full test suite**

```bash
.venv/Scripts/python manage.py test -v 1
```

Expected: All previous tests + new dashboard tests — all PASS.

---

**Step 12: Update ROADMAP.md**

Mark Phase 9 complete in the Completed section. Add `[x]` to all Tasks 23-32.

---

**Step 13: Final commit**

```bash
git add dashboard/ templates/admin_panel/ static/css/dashboard.css requirements.txt
git commit -m "feat: Phase 9 complete - guide dashboard foundation, tours CRUD, itinerary builder, guest manifest, activity library, guides tab, QR codes, photo gallery"
```

---

## Test Summary

Total new tests added across Tasks 23-32: **~35 tests**
Running after Phase 9: target **90+ total tests** (was 57 after Phase 6).

```bash
.venv/Scripts/python manage.py test -v 1
# Expected: XX tests, all PASS
```

---

## Context Processor Note

The `dev_mode` variable is currently passed manually in each view via `_dev_mode()`. If this pattern becomes cumbersome, an amendment task can extract it into a context processor:

```python
# overberg_adventures/context_processors.py
def dev_mode(request):
    from django.conf import settings
    return {'dev_mode': getattr(settings, 'DEV_MODE', False)}
```

Then add to `TEMPLATES[0]['OPTIONS']['context_processors']` in settings.py.

---

## Deferred to Phase 9b

- Revenue overview (Chart.js charts per tour: bookings, payment status)
- PDF export (guest manifest, itinerary, post-tour summary)
- Notification manager UI (Phase 8 dependency)
- Booking management UI (confirm/cancel RSVPs from dashboard)
- Multi-guide assignment per tour with roles
- Tour template cloning
