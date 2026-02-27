# Overstrand Adventures PWA — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a pixel-perfect PWA tour management app for Overstrand Adventures (adventure tourism, Overberg, South Africa) with a mobile-optimised Django admin panel, Google Maps, push notifications, NFC check-in, and a payment-agnostic booking system.

**Architecture:** Django 6 monolith with HTMX + Alpine.js for reactive UI — no separate frontend framework. All PWA screens are HTMX partial swaps off Django template views. Admin panel is a custom mobile-optimised Django view set (not default admin). Celery + Redis handles async tasks (emails, scheduled notifications).

**Tech Stack:** Django 6 · PostgreSQL · HTMX · Alpine.js · Bootstrap 5.3 · django-allauth · SendGrid (django-anymail) · Google Maps JS API v3 · Web Push (django-webpush) · Celery + Redis · GrapesJS · Docker + Portainer + Traefik

**Design reference:** `plannig/UI/` — 15 screenshots. Pixel-perfect match required.
**Design tokens:** bg `#FAF5EE`, primary `#F97316→#EA580C`, secondary `#0D9488`, cards white `border-radius:16px`

---

## Phase 1: Infrastructure & Docker

### Task 1: Create deploy folder with Traefik stack

**Files:**
- Create: `deploy/traefik/docker-compose.yml`
- Create: `deploy/traefik/traefik.yml`
- Create: `deploy/traefik/.env.example`

**Step 1: Create deploy directory structure**
```bash
mkdir -p deploy/traefik deploy/portainer deploy/redis deploy/app
```

**Step 2: Write Traefik compose file**

`deploy/traefik/docker-compose.yml`:
```yaml
services:
  traefik:
    image: traefik:v3.1
    container_name: traefik
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"   # Traefik dashboard (disable in prod)
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yml:/traefik.yml:ro
      - traefik_certs:/certs
    networks:
      - traefik_net

volumes:
  traefik_certs:

networks:
  traefik_net:
    name: traefik_net
    external: false
```

`deploy/traefik/traefik.yml`:
```yaml
api:
  dashboard: true
  insecure: true   # dev only — lock down in prod

entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"

providers:
  docker:
    exposedByDefault: false
    network: traefik_net

log:
  level: INFO
```

**Step 3: Run verify (no test needed — infra file)**
```bash
docker compose -f deploy/traefik/docker-compose.yml config
```
Expected: Valid YAML output, no errors.

**Step 4: Commit**
```bash
git add deploy/traefik/
git commit -m "infra: add Traefik stack"
```

---

### Task 2: Create Portainer and Redis stacks

**Files:**
- Create: `deploy/portainer/docker-compose.yml`
- Create: `deploy/redis/docker-compose.yml`

**Step 1: Write Portainer compose**

`deploy/portainer/docker-compose.yml`:
```yaml
services:
  portainer:
    image: portainer/portainer-ce:latest
    container_name: portainer
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer_data:/data
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.portainer.rule=PathPrefix(`/portainer`)"
      - "traefik.http.services.portainer.loadbalancer.server.port=9000"
    networks:
      - traefik_net

volumes:
  portainer_data:

networks:
  traefik_net:
    external: true
```

**Step 2: Write Redis compose**

`deploy/redis/docker-compose.yml`:
```yaml
services:
  redis:
    image: redis:7-alpine
    container_name: redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    networks:
      - traefik_net

volumes:
  redis_data:

networks:
  traefik_net:
    external: true
```

**Step 3: Validate both**
```bash
docker compose -f deploy/portainer/docker-compose.yml config
docker compose -f deploy/redis/docker-compose.yml config
```

**Step 4: Commit**
```bash
git add deploy/portainer/ deploy/redis/
git commit -m "infra: add Portainer and Redis stacks"
```

---

### Task 3: Create app Docker stack

**Files:**
- Create: `deploy/app/docker-compose.yml`
- Create: `Dockerfile`
- Create: `.env.example`
- Create: `.dockerignore`

**Step 1: Write Dockerfile**

`Dockerfile`:
```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "overberg_adventures.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

**Step 2: Write app compose**

`deploy/app/docker-compose.yml`:
```yaml
services:
  web:
    image: ghcr.io/YOUR_GITHUB_ORG/overberg-adventures:latest
    container_name: oa_web
    restart: unless-stopped
    env_file: .env
    depends_on:
      - db
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.oa.rule=PathPrefix(`/`)"
      - "traefik.http.services.oa.loadbalancer.server.port=8000"
    networks:
      - traefik_net

  db:
    image: postgres:16-alpine
    container_name: oa_db
    restart: unless-stopped
    volumes:
      - pg_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    networks:
      - traefik_net

  celery:
    image: ghcr.io/YOUR_GITHUB_ORG/overberg-adventures:latest
    container_name: oa_celery
    restart: unless-stopped
    env_file: .env
    command: celery -A overberg_adventures worker -l info
    depends_on:
      - db
    networks:
      - traefik_net

  celery-beat:
    image: ghcr.io/YOUR_GITHUB_ORG/overberg-adventures:latest
    container_name: oa_celery_beat
    restart: unless-stopped
    env_file: .env
    command: celery -A overberg_adventures beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    depends_on:
      - db
    networks:
      - traefik_net

volumes:
  pg_data:

networks:
  traefik_net:
    external: true
```

**Step 3: Write .env.example**

`.env.example`:
```bash
# Django
DJANGO_SECRET_KEY=change-me-in-production
DEBUG=True
ALLOWED_HOSTS=*
DEV_MODE=True

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=overberg_adventures
DB_USER=oa_user
DB_PASSWORD=changeme
DB_HOST=db
DB_PORT=5432

# Email (SendGrid)
SENDGRID_API_KEY=
DEFAULT_FROM_EMAIL=noreply@overstrandadventures.co.za

# Google Maps
GOOGLE_MAPS_API_KEY=

# Social Auth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=

# Web Push (VAPID keys — generate with: python manage.py generate_vapid_keys)
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
VAPID_ADMIN_EMAIL=admin@overstrandadventures.co.za

# Payment Gateway
PAYMENT_GATEWAY=manual  # manual | payfast | peach

# Redis
REDIS_URL=redis://redis:6379/0
```

**Step 4: Commit**
```bash
git add Dockerfile .env.example .dockerignore deploy/app/
git commit -m "infra: add app Docker stack and Dockerfile"
```

---

### Task 4: SSH setup documentation

**Files:**
- Create: `deploy/SSH_SETUP.md`

**Step 1: Write SSH setup guide**

`deploy/SSH_SETUP.md`:
```markdown
# VM SSH Passwordless Setup

## On your dev machine (run once):

```bash
# Generate ed25519 key (if you don't have one)
ssh-keygen -t ed25519 -C "overstrand-adventures-dev"

# Copy public key to VM (you'll need the password once)
ssh-copy-id -i ~/.ssh/id_ed25519.pub USER@VM_IP

# Add to ~/.ssh/config for convenience
cat >> ~/.ssh/config << 'EOF'
Host oa-vm
    HostName VM_IP
    User USER
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
EOF

# Test passwordless access
ssh oa-vm "echo connected"
```

## On the VM (after first passwordless login):

```bash
# Disable password authentication
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

## Install Docker on VM:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in
docker --version
```

## Deploy stacks on VM:

```bash
# 1. Traefik first (creates traefik_net)
scp -r deploy/traefik oa-vm:~/stacks/
ssh oa-vm "cd ~/stacks/traefik && docker compose up -d"

# 2. Portainer
scp -r deploy/portainer oa-vm:~/stacks/
ssh oa-vm "cd ~/stacks/portainer && docker compose up -d"

# 3. Redis
scp -r deploy/redis oa-vm:~/stacks/
ssh oa-vm "cd ~/stacks/redis && docker compose up -d"

# 4. App (deployed manually from GitHub by client — see Portainer UI)
```
```

**Step 2: Commit**
```bash
git add deploy/SSH_SETUP.md
git commit -m "infra: add SSH setup and VM deployment guide"
```

---

## Phase 2: Django Project Restructure

### Task 5: Restructure Django project and install dependencies

**Files:**
- Create: `requirements.txt`
- Modify: `overberg_adventures/settings.py`
- Create: `overberg_adventures/settings_dev.py`
- Create: `apps/` directory (move all apps here)

**Step 1: Write requirements.txt**

`requirements.txt`:
```
django==6.0.2
psycopg2-binary==2.9.9
djangorestframework==3.15.2
django-allauth[socialaccount]==65.3.0
django-allauth[mfa]==65.3.0
django-anymail[sendgrid]==12.0
django-webpush==0.3.3
celery[redis]==5.4.0
django-celery-beat==2.7.0
redis==5.2.1
gunicorn==23.0.0
whitenoise==6.8.0
pillow==11.1.0
python-decouple==3.8
django-ratelimit==4.1.0
# Dev only
django-debug-toolbar==4.4.6
```

**Step 2: Install**
```bash
pip install -r requirements.txt
```

**Step 3: Create apps directory and move dashboard**
```bash
mkdir -p apps
# We'll create all new apps in apps/ — dashboard stays at root level as admin shell
```

**Step 4: Rewrite settings.py**

`overberg_adventures/settings.py`:
```python
import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('DJANGO_SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
DEV_MODE = config('DEV_MODE', default=False, cast=bool) and DEBUG  # DEV_MODE only when DEBUG=True

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    # Third party
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',
    'anymail',
    'webpush',
    'django_celery_beat',
    # Project apps
    'apps.accounts',
    'apps.tours',
    'apps.bookings',
    'apps.payments',
    'apps.notifications',
    'apps.maps',
    'apps.nfc',
    'apps.landing',
    'apps.sos',
    'apps.backups',
    'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'apps.landing.middleware.MaintenanceModeMiddleware',
]

ROOT_URLCONF = 'overberg_adventures.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.accounts.context_processors.dev_mode',
            ],
        },
    },
]

WSGI_APPLICATION = 'overberg_adventures.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.sqlite3'),
        'NAME': config('DB_NAME', default=BASE_DIR / 'db.sqlite3'),
        'USER': config('DB_USER', default=''),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default=''),
        'PORT': config('DB_PORT', default=''),
    }
}

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SITE_ID = 1
TIME_ZONE = 'Africa/Johannesburg'
USE_I18N = True
USE_TZ = True

# Auth
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
LOGIN_REDIRECT_URL = '/app/'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_LOGIN_BY_CODE_ENABLED = True  # OTP email codes
ACCOUNT_LOGIN_BY_CODE_REQUIRED = True

# Email
ANYMAIL = {'SENDGRID_API_KEY': config('SENDGRID_API_KEY', default='')}
EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@localhost')

# Celery
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Google Maps
GOOGLE_MAPS_API_KEY = config('GOOGLE_MAPS_API_KEY', default='')

# Web Push
WEBPUSH_SETTINGS = {
    'VAPID_PUBLIC_KEY': config('VAPID_PUBLIC_KEY', default=''),
    'VAPID_PRIVATE_KEY': config('VAPID_PRIVATE_KEY', default=''),
    'VAPID_ADMIN_EMAIL': config('VAPID_ADMIN_EMAIL', default='admin@localhost'),
}

# Payment
PAYMENT_GATEWAY = config('PAYMENT_GATEWAY', default='manual')

# Dev mode context
DEV_MODE = DEV_MODE  # Exported for templates
```

**Step 5: Run Django check**
```bash
python manage.py check
```
Expected: No issues raised.

**Step 6: Commit**
```bash
git add requirements.txt overberg_adventures/settings.py
git commit -m "feat: restructure Django settings with decouple, all integrations configured"
```

---

### Task 6: Create all Django app skeletons

**Files:** Create `apps/__init__.py` and one folder per app

**Step 1: Create app skeletons**
```bash
mkdir -p apps
touch apps/__init__.py
for app in accounts tours bookings payments notifications maps nfc landing sos backups; do
    python manage.py startapp $app apps/$app
    echo "from django.apps import AppConfig
class $(echo ${app^})Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.$app'" > apps/$app/apps.py
done
```

**Step 2: Create initial migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```
Expected: Applied 0 migrations (empty models), Django system tables created.

**Step 3: Commit**
```bash
git add apps/
git commit -m "feat: scaffold all Django app directories"
```

---

## Phase 3: Authentication System

### Task 7: Email OTP verification model + flow

**Files:**
- Modify: `apps/accounts/models.py`
- Create: `apps/accounts/views.py`
- Create: `apps/accounts/urls.py`
- Create: `templates/accounts/login.html`
- Create: `templates/accounts/verify_otp.html`

**Step 1: Write failing test**

`apps/accounts/tests/test_otp.py`:
```python
import pytest
from django.contrib.auth import get_user_model
from apps.accounts.models import EmailOTP

User = get_user_model()

@pytest.mark.django_db
def test_otp_created_for_new_user():
    user = User.objects.create_user(email='test@example.com', password='x')
    otp = EmailOTP.objects.create_for_user(user)
    assert len(otp.code) == 6
    assert otp.code.isdigit()
    assert not otp.is_verified

@pytest.mark.django_db
def test_otp_expires_after_15_minutes():
    from django.utils import timezone
    from datetime import timedelta
    user = User.objects.create_user(email='a@b.com', password='x')
    otp = EmailOTP.objects.create_for_user(user)
    otp.created_at = timezone.now() - timedelta(minutes=16)
    otp.save()
    assert otp.is_expired

@pytest.mark.django_db
def test_otp_max_attempts():
    user = User.objects.create_user(email='c@d.com', password='x')
    otp = EmailOTP.objects.create_for_user(user)
    otp.attempts = 3
    assert otp.is_locked_out
```

**Step 2: Run test to verify it fails**
```bash
pytest apps/accounts/tests/test_otp.py -v
```
Expected: FAIL — `EmailOTP` not defined.

**Step 3: Write model**

`apps/accounts/models.py`:
```python
import random
from datetime import timedelta
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class EmailOTPManager(models.Manager):
    def create_for_user(self, user):
        self.filter(user=user, is_verified=False).delete()
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        return self.create(user=user, code=code)


class EmailOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)

    objects = EmailOTPManager()

    @property
    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=15)

    @property
    def is_locked_out(self):
        return self.attempts >= 3

    class Meta:
        ordering = ['-created_at']
```

**Step 4: Run test**
```bash
python manage.py makemigrations accounts
pytest apps/accounts/tests/test_otp.py -v
```
Expected: 3 PASSED.

**Step 5: Commit**
```bash
git add apps/accounts/
git commit -m "feat: EmailOTP model with expiry and lockout"
```

---

### Task 8: Auth views — login page + OTP verify

**Files:**
- Modify: `apps/accounts/views.py`
- Create: `apps/accounts/urls.py`
- Create: `templates/accounts/login.html`
- Create: `templates/accounts/verify_otp.html`

**Step 1: Write failing test**

`apps/accounts/tests/test_auth_views.py`:
```python
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_login_page_renders(client):
    response = client.get(reverse('accounts:login'))
    assert response.status_code == 200
    assert b'Continue with Google' in response.content

@pytest.mark.django_db
def test_email_signup_sends_otp(client, mailoutbox):
    response = client.post(reverse('accounts:email_signup'), {
        'email': 'newuser@test.com'
    })
    assert response.status_code in [200, 302]
    assert len(mailoutbox) == 1
    assert 'verification' in mailoutbox[0].subject.lower()

@pytest.mark.django_db
def test_otp_verify_correct_code(client):
    from apps.accounts.models import EmailOTP
    user = User.objects.create_user(email='v@test.com', password='x')
    otp = EmailOTP.objects.create_for_user(user)
    client.force_login(user)
    response = client.post(reverse('accounts:verify_otp'), {'code': otp.code})
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.emailaddress_set.filter(verified=True).exists() or \
           getattr(user, 'profile', None) is not None
```

**Step 2: Run to verify fail**
```bash
pytest apps/accounts/tests/test_auth_views.py -v
```
Expected: FAIL — no URL 'accounts:login'.

**Step 3: Write views**

`apps/accounts/views.py`:
```python
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, login
from django.contrib import messages
from django.conf import settings
from .models import EmailOTP
from .emails import send_otp_email

User = get_user_model()


def login_page(request):
    """Main login/signup page with Google, Facebook, Email options."""
    if request.user.is_authenticated:
        return redirect('app:home')
    return render(request, 'accounts/login.html', {
        'dev_mode': settings.DEV_MODE,
    })


def email_signup(request):
    """Accept email → create/get user → send OTP."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        if not email:
            messages.error(request, 'Email is required.')
            return redirect('accounts:login')
        user, created = User.objects.get_or_create(
            email=email,
            defaults={'username': email, 'is_active': False}
        )
        otp = EmailOTP.objects.create_for_user(user)
        if settings.DEV_MODE:
            # In dev mode: show OTP in session so it can be pre-filled
            request.session['dev_otp'] = otp.code
        else:
            send_otp_email(user, otp.code)
        request.session['otp_user_id'] = user.pk
        return redirect('accounts:verify_otp')
    return redirect('accounts:login')


def verify_otp(request):
    """Verify OTP code — activate user and log in."""
    user_id = request.session.get('otp_user_id')
    if not user_id:
        return redirect('accounts:login')
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return redirect('accounts:login')

    otp = EmailOTP.objects.filter(user=user, is_verified=False).first()
    dev_otp = request.session.get('dev_otp') if settings.DEV_MODE else None

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        if not otp or otp.is_expired or otp.is_locked_out:
            messages.error(request, 'Code expired or too many attempts. Request a new one.')
            return redirect('accounts:login')
        if code == otp.code:
            otp.is_verified = True
            otp.save()
            user.is_active = True
            user.save()
            from allauth.account.models import EmailAddress
            EmailAddress.objects.get_or_create(
                user=user, email=user.email,
                defaults={'primary': True, 'verified': True}
            )
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            del request.session['otp_user_id']
            request.session.pop('dev_otp', None)
            return redirect('accounts:profile_setup')
        else:
            otp.attempts += 1
            otp.save()
            messages.error(request, 'Incorrect code. Try again.')

    return render(request, 'accounts/verify_otp.html', {
        'dev_otp': dev_otp,
        'dev_mode': settings.DEV_MODE,
    })
```

**Step 4: Write URLs**

`apps/accounts/urls.py`:
```python
from django.urls import path
from . import views

app_name = 'accounts'
urlpatterns = [
    path('login/', views.login_page, name='login'),
    path('signup/email/', views.email_signup, name='email_signup'),
    path('verify/', views.verify_otp, name='verify_otp'),
    path('setup/', views.profile_setup, name='profile_setup'),
]
```

**Step 5: Write login template** (pixel-perfect to prototype — warm cream bg, orange gradient CTA)

`templates/accounts/login.html`:
```html
{% extends "base_app.html" %}
{% block content %}
<div class="min-vh-100 d-flex flex-column align-items-center justify-content-center px-4"
     style="background:#FAF5EE">
  <img src="{% static 'img/logo.png' %}" alt="Overstrand Adventures" class="mb-4" style="width:200px">
  <h1 class="fw-bold mb-1 text-center">Welcome</h1>
  <p class="text-muted text-center mb-5">Sign in or create your account</p>

  <!-- Social buttons -->
  <a href="{% provider_login_url 'google' %}"
     class="btn btn-outline-secondary w-100 mb-3 d-flex align-items-center gap-2">
    <img src="{% static 'img/google-icon.svg' %}" width="20"> Continue with Google
  </a>
  <a href="{% provider_login_url 'facebook' %}"
     class="btn btn-outline-secondary w-100 mb-4 d-flex align-items-center gap-2">
    <img src="{% static 'img/facebook-icon.svg' %}" width="20"> Continue with Facebook
  </a>

  <div class="d-flex align-items-center w-100 mb-4">
    <hr class="flex-grow-1"><span class="px-3 text-muted small">or</span><hr class="flex-grow-1">
  </div>

  <!-- Email form -->
  <form method="post" action="{% url 'accounts:email_signup' %}" class="w-100">
    {% csrf_token %}
    <input type="email" name="email" class="form-control mb-3" placeholder="Email address" required>
    <button type="submit" class="btn w-100 py-3 fw-semibold text-white"
            style="background:linear-gradient(135deg,#F97316,#EA580C);border-radius:14px">
      Continue with Email
    </button>
  </form>

  {% if dev_mode %}
  <div class="mt-4 p-3 border border-warning rounded w-100" style="background:#FFFBEB">
    <small class="text-warning fw-bold">⚠ DEV MODE — Quick login</small>
    <form method="post" action="{% url 'accounts:dev_login' %}" class="mt-2">
      {% csrf_token %}
      <input type="email" name="email" class="form-control form-control-sm mb-2"
             placeholder="dev@test.com" value="dev@test.com">
      <button class="btn btn-warning btn-sm w-100">Dev Login (bypass OAuth)</button>
    </form>
  </div>
  {% endif %}
</div>
{% endblock %}
```

**Step 6: Run tests**
```bash
pytest apps/accounts/tests/test_auth_views.py -v
```
Expected: 3 PASSED.

**Step 7: Commit**
```bash
git add apps/accounts/ templates/accounts/
git commit -m "feat: auth views - login page, email OTP signup, OTP verify with dev mode"
```

---

### Task 9: UserProfile model (5-step wizard data)

**Files:**
- Modify: `apps/accounts/models.py`
- Create: `apps/accounts/tests/test_profile.py`

**Step 1: Write failing test**

```python
@pytest.mark.django_db
def test_profile_created_on_user_creation():
    user = User.objects.create_user(email='p@test.com', password='x')
    assert hasattr(user, 'profile')
    assert user.profile.fitness_level == 3  # default middle

@pytest.mark.django_db
def test_profile_setup_complete_flag():
    user = User.objects.create_user(email='q@test.com', password='x')
    assert not user.profile.setup_complete
    user.profile.indemnity_accepted = True
    user.profile.first_name = 'Test'
    user.profile.save()
    assert user.profile.setup_complete
```

**Step 2: Run to verify fail**
```bash
pytest apps/accounts/tests/test_profile.py -v
```

**Step 3: Write UserProfile model**

Add to `apps/accounts/models.py`:
```python
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    class Role(models.TextChoices):
        GUEST = 'GUEST', 'Guest Traveller'
        GUIDE = 'GUIDE', 'Tour Guide'
        OPERATOR = 'OPERATOR', 'Operator'
        ADMIN = 'ADMIN', 'Admin'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.GUEST)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone_whatsapp = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    # Step 2: Health
    fitness_level = models.PositiveSmallIntegerField(default=3)  # 1-5
    medical_conditions = models.TextField(blank=True)
    dietary_requirements = models.TextField(blank=True)
    # Step 4: Notes
    personal_notes = models.TextField(blank=True)
    # Step 5: Indemnity
    indemnity_accepted = models.BooleanField(default=False)
    indemnity_accepted_at = models.DateTimeField(null=True, blank=True)
    # Settings
    location_enabled = models.BooleanField(default=False)
    notifications_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def setup_complete(self):
        return bool(self.first_name and self.indemnity_accepted)

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.user.email


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
```

**Step 4: Run tests**
```bash
python manage.py makemigrations accounts && python manage.py migrate
pytest apps/accounts/tests/test_profile.py -v
```
Expected: PASSED.

**Step 5: Commit**
```bash
git add apps/accounts/
git commit -m "feat: UserProfile model with 5-step wizard fields, auto-create on user"
```

---

### Task 10: Profile setup wizard views (5 steps, HTMX)

**Files:**
- Modify: `apps/accounts/views.py`
- Create: `templates/accounts/setup/wizard.html`
- Create: `templates/accounts/setup/step1_personal.html`
- Create: `templates/accounts/setup/step2_health.html`
- Create: `templates/accounts/setup/step3_permissions.html`
- Create: `templates/accounts/setup/step4_notes.html`
- Create: `templates/accounts/setup/step5_indemnity.html`

**Step 1: Write failing test**
```python
@pytest.mark.django_db
def test_profile_setup_step1_post(client):
    user = User.objects.create_user(email='s@test.com', password='x')
    client.force_login(user)
    response = client.post(reverse('accounts:profile_setup_step', args=[1]), {
        'first_name': 'John', 'last_name': 'Doe',
        'phone_whatsapp': '+27821234567', 'date_of_birth': '1990-01-01',
    }, HTTP_HX_REQUEST='true')
    assert response.status_code == 200
    user.profile.refresh_from_db()
    assert user.profile.first_name == 'John'
```

**Step 2: Run to verify fail**
```bash
pytest apps/accounts/tests/test_profile_wizard.py -v
```

**Step 3: Write wizard view**

`apps/accounts/views.py` (add):
```python
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone

WIZARD_STEPS = 5

class ProfileSetupView(LoginRequiredMixin, View):
    def get(self, request, step=1):
        profile = request.user.profile
        if profile.setup_complete:
            return redirect('app:home')
        template = f'accounts/setup/step{step}_{self._step_name(step)}.html'
        return render(request, 'accounts/setup/wizard.html', {
            'step': step, 'total': WIZARD_STEPS, 'profile': profile,
            'step_template': template,
        })

    def post(self, request, step=1):
        profile = request.user.profile
        if step == 1:
            profile.first_name = request.POST.get('first_name', '').strip()
            profile.last_name = request.POST.get('last_name', '').strip()
            profile.phone_whatsapp = request.POST.get('phone_whatsapp', '').strip()
            dob = request.POST.get('date_of_birth')
            if dob:
                from datetime import date
                profile.date_of_birth = date.fromisoformat(dob)
        elif step == 2:
            profile.fitness_level = int(request.POST.get('fitness_level', 3))
            profile.medical_conditions = request.POST.get('medical_conditions', '')
            profile.dietary_requirements = request.POST.get('dietary_requirements', '')
        elif step == 3:
            profile.location_enabled = request.POST.get('location_enabled') == 'true'
            profile.notifications_enabled = request.POST.get('notifications_enabled') == 'true'
        elif step == 4:
            profile.personal_notes = request.POST.get('personal_notes', '')
        elif step == 5:
            if request.POST.get('indemnity_accepted') == 'on':
                profile.indemnity_accepted = True
                profile.indemnity_accepted_at = timezone.now()
        profile.save()

        if step < WIZARD_STEPS:
            next_step = step + 1
            if request.headers.get('HX-Request'):
                template = f'accounts/setup/step{next_step}_{self._step_name(next_step)}.html'
                return render(request, template, {'step': next_step, 'total': WIZARD_STEPS, 'profile': profile})
            return redirect('accounts:profile_setup_step', step=next_step)
        return redirect('app:home')

    @staticmethod
    def _step_name(step):
        return {1: 'personal', 2: 'health', 3: 'permissions', 4: 'notes', 5: 'indemnity'}[step]
```

**Step 4: Run tests**
```bash
pytest apps/accounts/tests/test_profile_wizard.py -v
```
Expected: PASSED.

**Step 5: Commit**
```bash
git add apps/accounts/ templates/accounts/setup/
git commit -m "feat: 5-step profile setup wizard with HTMX partial step swaps"
```

---

## Phase 4: Tours System

### Task 11: ActivityCategory model + seed script

**Files:**
- Create: `apps/tours/models.py`
- Create: `apps/tours/fixtures/activity_categories.json`
- Create: `apps/tours/management/commands/seed_categories.py`

**Step 1: Write failing test**
```python
@pytest.mark.django_db
def test_activity_category_created():
    from apps.tours.models import ActivityCategory
    cat = ActivityCategory.objects.create(
        name='Hiking', icon='mountain', colour='#F97316'
    )
    assert str(cat) == 'Hiking'

@pytest.mark.django_db
def test_seed_categories_creates_defaults(call_command):
    call_command('seed_categories')
    from apps.tours.models import ActivityCategory
    assert ActivityCategory.objects.filter(name='Hiking').exists()
    assert ActivityCategory.objects.filter(name='Food & Dining').exists()
```

**Step 2: Write models**

`apps/tours/models.py`:
```python
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ActivityCategory(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, default='map-pin')  # Lucide/Bootstrap icon name
    colour = models.CharField(max_length=7, default='#F97316')  # hex
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Activity Categories'

    def __str__(self):
        return self.name
```

**Step 3: Write seed command**

`apps/tours/management/commands/seed_categories.py`:
```python
from django.core.management.base import BaseCommand
from apps.tours.models import ActivityCategory

INITIAL_CATEGORIES = [
    {'name': 'Hiking', 'icon': 'mountain', 'colour': '#F97316', 'order': 1},
    {'name': 'Food & Dining', 'icon': 'utensils', 'colour': '#0D9488', 'order': 2},
    {'name': 'Kayaking', 'icon': 'waves', 'colour': '#0284C7', 'order': 3},
    {'name': 'Cycling', 'icon': 'bike', 'colour': '#7C3AED', 'order': 4},
    {'name': 'Scenic Drive', 'icon': 'car', 'colour': '#D97706', 'order': 5},
    {'name': 'Whale Watching', 'icon': 'anchor', 'colour': '#0891B2', 'order': 6},
    {'name': 'Swimming', 'icon': 'waves', 'colour': '#2563EB', 'order': 7},
    {'name': 'Photography', 'icon': 'camera', 'colour': '#DB2777', 'order': 8},
    {'name': 'Cultural', 'icon': 'landmark', 'colour': '#65A30D', 'order': 9},
    {'name': 'Accommodation', 'icon': 'bed', 'colour': '#6B7280', 'order': 10},
]

class Command(BaseCommand):
    help = 'Seed initial activity categories'

    def handle(self, *args, **options):
        for data in INITIAL_CATEGORIES:
            ActivityCategory.objects.get_or_create(name=data['name'], defaults=data)
        self.stdout.write(self.style.SUCCESS(f'Seeded {len(INITIAL_CATEGORIES)} categories'))
```

**Step 4: Run tests + seed**
```bash
python manage.py makemigrations tours
python manage.py migrate
pytest apps/tours/tests/test_categories.py -v
python manage.py seed_categories
```
Expected: Tests pass, categories seeded.

**Step 5: Commit**
```bash
git add apps/tours/
git commit -m "feat: ActivityCategory model with seed command (9 initial categories)"
```

---

### Task 12: Tour and ItineraryItem models

**Files:**
- Modify: `apps/tours/models.py`
- Create: `apps/tours/tests/test_tour_model.py`

**Step 1: Write failing tests**
```python
@pytest.mark.django_db
def test_tour_code_is_unique(tour_factory):
    t1 = tour_factory(tour_code='fynbos')
    with pytest.raises(Exception):
        tour_factory(tour_code='fynbos')  # duplicate code

@pytest.mark.django_db
def test_tour_itinerary_ordered_by_day_and_order(tour_factory, category_factory):
    tour = tour_factory()
    from apps.tours.models import ItineraryItem
    i2 = ItineraryItem.objects.create(tour=tour, day=1, order=2, title='Lunch', ...)
    i1 = ItineraryItem.objects.create(tour=tour, day=1, order=1, title='Breakfast', ...)
    items = list(tour.itinerary_items.all())
    assert items[0].title == 'Breakfast'
```

**Step 2: Write models (add to tours/models.py)**

```python
class TourCodeWord(models.Model):
    word = models.CharField(max_length=50, unique=True)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def generate(cls):
        """Pick a random unused word; raise if exhausted."""
        word = cls.objects.filter(is_used=False).order_by('?').first()
        if not word:
            raise ValueError('No tour code words available — add more to TourCodeWord')
        word.is_used = True
        word.used_at = timezone.now()
        word.save()
        return word.word


class Tour(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    guide = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='guided_tours')
    tour_code = models.CharField(max_length=50, unique=True, blank=True)
    start_datetime = models.DateTimeField()
    location_name = models.CharField(max_length=200)
    location_lat = models.DecimalField(max_digits=10, decimal_places=7)
    location_lng = models.DecimalField(max_digits=10, decimal_places=7)
    capacity = models.PositiveSmallIntegerField(default=20)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    polygon = models.JSONField(null=True, blank=True)  # GeoJSON polygon
    min_fitness_level = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ItineraryItem(models.Model):
    class Difficulty(models.TextChoices):
        EASY = 'EASY', 'Easy'
        MODERATE = 'MODERATE', 'Moderate'
        HARD = 'HARD', 'Hard'

    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='itinerary_items')
    day = models.PositiveSmallIntegerField(default=1)
    order = models.PositiveSmallIntegerField(default=0)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(ActivityCategory, on_delete=models.SET_NULL, null=True)
    start_time = models.TimeField()
    duration_minutes = models.PositiveSmallIntegerField(default=60)
    location_name = models.CharField(max_length=200, blank=True)
    location_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    location_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, default=Difficulty.EASY)
    distance_km = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    class Meta:
        ordering = ['day', 'order']
```

**Step 3: Migrate + test**
```bash
python manage.py makemigrations tours && python manage.py migrate
pytest apps/tours/tests/ -v
```

**Step 4: Commit**
```bash
git add apps/tours/
git commit -m "feat: Tour, ItineraryItem, TourCodeWord models"
```

---

## Phase 5: Bookings + Payment Adapter

### Task 13: Booking model + RSVP flow

**Files:**
- Create: `apps/bookings/models.py`
- Create: `apps/bookings/tests/test_booking.py`

**Step 1: Write failing test**
```python
@pytest.mark.django_db
def test_booking_created_from_rsvp(user_factory, tour_factory):
    user = user_factory()
    tour = tour_factory(capacity=10)
    from apps.bookings.models import Booking
    booking = Booking.objects.create_from_rsvp(user=user, tour=tour)
    assert booking.status == Booking.Status.RSVP_PENDING
    assert tour.bookings.count() == 1

@pytest.mark.django_db
def test_tour_capacity_respected(user_factory, tour_factory):
    tour = tour_factory(capacity=1)
    u1, u2 = user_factory(), user_factory()
    from apps.bookings.models import Booking
    Booking.objects.create_from_rsvp(user=u1, tour=tour)
    with pytest.raises(ValueError, match='capacity'):
        Booking.objects.create_from_rsvp(user=u2, tour=tour)
```

**Step 2: Write model**

`apps/bookings/models.py`:
```python
from django.db import models
from django.contrib.auth import get_user_model
from apps.tours.models import Tour

User = get_user_model()


class BookingManager(models.Manager):
    def create_from_rsvp(self, user, tour):
        confirmed_count = self.filter(
            tour=tour, status__in=['RSVP_PENDING', 'CONFIRMED']
        ).count()
        if confirmed_count >= tour.capacity:
            raise ValueError(f'Tour at capacity ({tour.capacity})')
        return self.create(user=user, tour=tour, status=Booking.Status.RSVP_PENDING)


class Booking(models.Model):
    class Status(models.TextChoices):
        INVITED = 'INVITED', 'Invited'
        RSVP_PENDING = 'RSVP_PENDING', 'RSVP Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RSVP_PENDING)
    tour_code = models.CharField(max_length=50, blank=True)  # assigned after payment
    invited_at = models.DateTimeField(auto_now_add=True)
    rsvp_deadline = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    objects = BookingManager()

    class Meta:
        unique_together = [['tour', 'user']]
```

**Step 3: Migrate + test**
```bash
python manage.py makemigrations bookings && python manage.py migrate
pytest apps/bookings/tests/test_booking.py -v
```

**Step 4: Commit**
```bash
git add apps/bookings/
git commit -m "feat: Booking model with capacity validation and RSVP flow"
```

---

### Task 14: Payment adapter pattern

**Files:**
- Create: `apps/payments/adapters/__init__.py`
- Create: `apps/payments/adapters/base.py`
- Create: `apps/payments/adapters/manual.py`
- Create: `apps/payments/adapters/dev.py`
- Create: `apps/payments/models.py`
- Create: `apps/payments/tests/test_adapters.py`

**Step 1: Write failing test**
```python
def test_get_adapter_returns_manual_by_default(settings):
    settings.PAYMENT_GATEWAY = 'manual'
    from apps.payments.adapters import get_payment_adapter
    adapter = get_payment_adapter()
    from apps.payments.adapters.manual import ManualPaymentAdapter
    assert isinstance(adapter, ManualPaymentAdapter)

@pytest.mark.django_db
def test_dev_simulate_confirms_booking(booking_factory):
    from apps.payments.adapters.dev import DevSimulateAdapter
    booking = booking_factory(status='RSVP_PENDING')
    adapter = DevSimulateAdapter()
    result = adapter.simulate_payment(booking)
    assert result.success
    booking.refresh_from_db()
    assert booking.status == 'CONFIRMED'
    assert booking.tour_code != ''
```

**Step 2: Write base adapter**

`apps/payments/adapters/base.py`:
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class PaymentResult:
    success: bool
    reference: str = ''
    error: str = ''

class PaymentGatewayAdapter(ABC):
    @abstractmethod
    def create_payment_session(self, booking, amount_zar: int) -> dict:
        """Return redirect URL or form fields for payment page."""

    @abstractmethod
    def verify_webhook(self, request) -> PaymentResult:
        """Verify incoming webhook and return result."""

    @abstractmethod
    def process_confirmation(self, booking, result: PaymentResult) -> None:
        """Called after successful payment — assign tour code, send email, confirm booking."""
```

`apps/payments/adapters/__init__.py`:
```python
from django.conf import settings

def get_payment_adapter():
    gateway = getattr(settings, 'PAYMENT_GATEWAY', 'manual')
    if gateway == 'payfast':
        from .payfast import PayFastAdapter
        return PayFastAdapter()
    if gateway == 'peach':
        from .peach import PeachPaymentsAdapter
        return PeachPaymentsAdapter()
    if gateway == 'dev' or (gateway == 'manual' and settings.DEV_MODE):
        from .dev import DevSimulateAdapter
        return DevSimulateAdapter()
    from .manual import ManualPaymentAdapter
    return ManualPaymentAdapter()
```

`apps/payments/adapters/dev.py`:
```python
from .base import PaymentGatewayAdapter, PaymentResult
from django.utils import timezone

class DevSimulateAdapter(PaymentGatewayAdapter):
    """DEV_MODE only — instantly confirms any booking without real payment."""

    def create_payment_session(self, booking, amount_zar):
        return {'dev_simulate': True, 'booking_id': booking.pk}

    def verify_webhook(self, request):
        return PaymentResult(success=True, reference='DEV-SIM')

    def simulate_payment(self, booking):
        result = PaymentResult(success=True, reference='DEV-SIM')
        self.process_confirmation(booking, result)
        return result

    def process_confirmation(self, booking, result):
        from apps.tours.models import TourCodeWord
        from apps.notifications.tasks import send_tour_code_email
        booking.status = 'CONFIRMED'
        booking.tour_code = TourCodeWord.generate()
        booking.confirmed_at = timezone.now()
        booking.save()
        send_tour_code_email.delay(booking.pk)
```

`apps/payments/adapters/manual.py`:
```python
from .base import PaymentGatewayAdapter, PaymentResult

class ManualPaymentAdapter(PaymentGatewayAdapter):
    """Admin manually captures payment — no automated flow."""

    def create_payment_session(self, booking, amount_zar):
        return {'manual': True, 'instruction': 'Admin will capture payment manually.'}

    def verify_webhook(self, request):
        raise NotImplementedError('Manual payments do not use webhooks.')

    def process_confirmation(self, booking, result):
        from django.utils import timezone
        from apps.tours.models import TourCodeWord
        from apps.notifications.tasks import send_tour_code_email
        booking.status = 'CONFIRMED'
        booking.tour_code = TourCodeWord.generate()
        booking.confirmed_at = timezone.now()
        booking.save()
        send_tour_code_email.delay(booking.pk)
```

**Step 3: Run tests**
```bash
pytest apps/payments/tests/test_adapters.py -v
```
Expected: PASSED.

**Step 4: Commit**
```bash
git add apps/payments/
git commit -m "feat: payment adapter pattern - manual, dev simulate, base ABC"
```

---

## Phase 6: PWA Core Screens

### Task 15: Base templates + bottom nav + PWA shell

**Files:**
- Create: `templates/base_app.html`
- Create: `templates/app/partials/bottom_nav.html`
- Create: `static/css/app.css`
- Create: `static/manifest.json`
- Create: `static/js/service-worker.js`

**Step 1: Write base app template**

`templates/base_app.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="theme-color" content="#F97316">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <title>{% block title %}Overstrand Adventures{% endblock %}</title>
  <link rel="manifest" href="{% static 'manifest.json' %}">
  <link rel="stylesheet" href="{% static 'vendor/bootstrap/bootstrap.min.css' %}">
  <link rel="stylesheet" href="{% static 'css/app.css' %}">
  {% block extra_head %}{% endblock %}
</head>
<body style="background:#FAF5EE; padding-bottom:80px">

  {% if dev_mode %}
  <div class="dev-banner">⚠ DEV MODE ACTIVE</div>
  {% endif %}

  <main id="main-content" hx-boost="true">
    {% block content %}{% endblock %}
  </main>

  {% if user.is_authenticated %}
  {% include "app/partials/bottom_nav.html" %}
  {% endif %}

  <script src="{% static 'vendor/bootstrap/bootstrap.bundle.min.js' %}"></script>
  <script src="{% static 'vendor/htmx/htmx.min.js' %}"></script>
  <script src="{% static 'vendor/alpinejs/alpine.min.js' %}" defer></script>
  {% block extra_js %}{% endblock %}
  <script>
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/static/js/service-worker.js');
    }
  </script>
</body>
</html>
```

**Step 2: Write bottom nav**

`templates/app/partials/bottom_nav.html`:
```html
<nav class="bottom-nav fixed-bottom d-flex justify-content-around align-items-center px-2 py-2 bg-white border-top">
  <a href="{% url 'app:home' %}" class="bottom-nav__item {% if active_tab == 'home' %}active{% endif %}">
    <svg><!-- home icon --></svg>
    <span>Home</span>
  </a>
  <a href="{% url 'app:itinerary' %}" class="bottom-nav__item {% if active_tab == 'itinerary' %}active{% endif %}">
    <svg><!-- list icon --></svg>
    <span>Itinerary</span>
  </a>
  <a href="{% url 'app:sos' %}" class="bottom-nav__item {% if active_tab == 'sos' %}active{% endif %}">
    <svg><!-- triangle-alert icon --></svg>
    <span>SOS</span>
  </a>
  <a href="{% url 'app:map' %}" class="bottom-nav__item {% if active_tab == 'map' %}active{% endif %}">
    <svg><!-- map icon --></svg>
    <span>Map</span>
  </a>
  <a href="{% url 'app:profile' %}" class="bottom-nav__item {% if active_tab == 'profile' %}active{% endif %}">
    {% if request.user.profile.avatar %}
      <img src="{{ request.user.profile.avatar.url }}" class="avatar-xs rounded-circle">
    {% else %}
      <div class="avatar-xs rounded-circle bg-purple text-white d-flex align-items-center justify-content-center">
        {{ request.user.profile.first_name|first|lower }}
      </div>
    {% endif %}
    <span>Profile</span>
  </a>
</nav>
```

**Step 3: Write app.css (design tokens)**

`static/css/app.css`:
```css
:root {
  --color-bg: #FAF5EE;
  --color-primary: #F97316;
  --color-primary-dark: #EA580C;
  --color-secondary: #0D9488;
  --color-surface: #FFFFFF;
  --color-text: #1C1917;
  --color-text-muted: #78716C;
  --color-border: #E7E5E4;
  --color-danger: #EF4444;
}

body { background: var(--color-bg); color: var(--color-text); }

.btn-primary-oa {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  border: none;
  border-radius: 14px;
  color: white;
  font-weight: 600;
  padding: 14px 24px;
}

.card-oa {
  background: var(--color-surface);
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  border: none;
}

.bottom-nav { height: 70px; box-shadow: 0 -1px 0 var(--color-border); }
.bottom-nav__item { display: flex; flex-direction: column; align-items: center;
  font-size: 11px; color: var(--color-text-muted); text-decoration: none; gap: 4px; }
.bottom-nav__item.active { color: var(--color-primary); font-weight: 600; }

.progress-steps { display: flex; gap: 6px; }
.progress-step { height: 4px; border-radius: 2px; flex: 1; background: var(--color-border); }
.progress-step.done { background: var(--color-primary); }

.dev-banner { background: #F59E0B; color: white; text-align: center;
  font-size: 12px; font-weight: bold; padding: 4px; position: sticky; top: 0; z-index: 9999; }

.activity-marker { width: 44px; height: 44px; border-radius: 50%; display: flex;
  align-items: center; justify-content: center; border: 3px solid white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2); }

.label-xs { font-size: 11px; letter-spacing: 0.08em; color: var(--color-text-muted);
  text-transform: uppercase; font-weight: 500; }

.avatar-xs { width: 28px; height: 28px; font-size: 12px; }
.bg-purple { background: #7C3AED; }
```

**Step 4: Write PWA manifest**

`static/manifest.json`:
```json
{
  "name": "Overstrand Adventures",
  "short_name": "OA Tours",
  "description": "Your Overstrand adventure companion",
  "theme_color": "#F97316",
  "background_color": "#FAF5EE",
  "display": "standalone",
  "orientation": "portrait",
  "start_url": "/app/",
  "scope": "/app/",
  "icons": [
    {"src": "/static/img/icon-192.png", "sizes": "192x192", "type": "image/png"},
    {"src": "/static/img/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}
  ]
}
```

**Step 5: Basic service worker**

`static/js/service-worker.js`:
```javascript
const CACHE = 'oa-v1';
const STATIC = ['/static/css/app.css', '/static/manifest.json', '/app/offline/'];

self.addEventListener('install', e => e.waitUntil(
  caches.open(CACHE).then(c => c.addAll(STATIC))
));

self.addEventListener('fetch', e => {
  if (e.request.mode === 'navigate') {
    e.respondWith(fetch(e.request).catch(() => caches.match('/app/offline/')));
  }
});

self.addEventListener('push', e => {
  const data = e.data?.json() ?? {};
  e.waitUntil(self.registration.showNotification(data.title || 'Overstrand Adventures', {
    body: data.body || '',
    icon: '/static/img/icon-192.png',
    badge: '/static/img/badge-72.png',
    data: data,
  }));
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(clients.openWindow(e.notification.data?.url || '/app/'));
});
```

**Step 6: Commit**
```bash
git add templates/ static/
git commit -m "feat: PWA shell - base template, bottom nav, design tokens CSS, manifest, service worker"
```

---

### Task 16: Home screen view

**Files:**
- Create: `apps/tours/views_app.py`
- Create: `templates/app/home.html`
- Modify: `overberg_adventures/urls.py`

**Step 1: Write failing test**
```python
@pytest.mark.django_db
def test_home_view_no_tours(client, user_with_profile):
    client.force_login(user_with_profile)
    response = client.get(reverse('app:home'))
    assert response.status_code == 200
    assert b'ENTER TOUR CODE' in response.content

@pytest.mark.django_db
def test_home_view_with_tours(client, user_with_booking):
    client.force_login(user_with_booking.user)
    response = client.get(reverse('app:home'))
    assert b'MY TOURS' in response.content
```

**Step 2: Write view + template** (matches prototype exactly — logo, welcome, tour code input, "Discover" orange CTA, "MY TOURS" section with booking cards)

*Implementation follows prototype screenshots exactly — see plannig/UI/1000220114.jpg and 1000220122.jpg*

**Step 3: Tour code join view + HTMX partial**
- POST `/app/tours/join/` → looks up tour by code → returns tour preview card partial (1000220116.jpg)
- Confirm → creates booking → redirects to itinerary

**Step 4: Commit**
```bash
git commit -m "feat: home screen - tour code entry, my tours list, join tour flow"
```

---

### Task 17: Itinerary view

**Files:**
- Create: `templates/app/itinerary.html`
- Create: `templates/app/partials/itinerary_day.html`
- Create: `templates/app/partials/activity_card.html`

*Reference: plannig/UI/1000220118.jpg and 1000220120.jpg*

- Top: Google Maps satellite partial (250px height) with markers
- Invite banner (HTMX-loaded if RSVP_PENDING)
- Tour metadata row (start time, location + Directions link, guide + Contact WhatsApp link)
- Day sections (collapsible, HTMX): activity cards per day ordered by time
- Activity card: category circle icon (colour-coded), title, location, time badge, difficulty/duration/distance, category tag pill

**Commit:** `feat: itinerary view with day timeline and activity cards`

---

### Task 18: Map tab

**Files:**
- Create: `templates/app/map.html`
- Create: `static/js/map-app.js`

*Reference: plannig/UI/1000220126.jpg*

- Full-screen Google Maps (satellite, no UI chrome)
- Markers loaded via HTMX from `/app/api/tour-markers/<booking_id>/` JSON endpoint
- Polygon overlay if tour has polygon GeoJSON
- Route polylines if tour has waypoints
- Left control panel: zoom +/−, layer toggle, locate-me, compass (Alpine.js)
- Bottom pill: "View Itinerary" → slides up itinerary drawer (Alpine.js x-show + transition)

**Step 1: Map init JS**

`static/js/map-app.js`:
```javascript
let map;
async function initMap(lat, lng, bookingId) {
  const { Map } = await google.maps.importLibrary('maps');
  map = new Map(document.getElementById('map'), {
    center: { lat, lng },
    zoom: 13,
    mapTypeId: 'satellite',
    disableDefaultUI: true,
    zoomControl: false,
  });
  loadMarkers(bookingId);
  loadPolygon(bookingId);
  loadRoutes(bookingId);
}

async function loadMarkers(bookingId) {
  const res = await fetch(`/app/api/tour-markers/${bookingId}/`);
  const data = await res.json();
  data.markers.forEach(m => {
    new google.maps.Marker({
      position: { lat: m.lat, lng: m.lng },
      map,
      icon: buildCircleMarker(m.colour, m.icon),
      title: m.title,
    });
  });
}
```

**Commit:** `feat: map tab - satellite view, markers, polygon overlay, route polylines, itinerary drawer`

---

### Task 19: Profile tab

*Reference: plannig/UI/1000220128.jpg and 1000220130.jpg*

- Orange gradient header card (avatar, name, role, Edit Profile button)
- Personal Details card
- Health & Diet card
- Notes card
- App Settings card (location toggle, notifications toggle — updates profile via HTMX POST)
- Edit profile → HTMX inline form swap

**Commit:** `feat: profile tab - all sections, edit inline, settings toggles`

---

### Task 20: SOS screen

*Reference: concept from prototype — no screenshot, design based on brief*

- Large red SOS button (full-width, prominent) — tap → confirmation modal → triggers configured SOS actions
- SOS Config (loaded from DB per superuser toggles):
  - Notify guide: POST to `/app/sos/alert/` → sends push notification + WhatsApp link to guide
  - Notify emergency contacts: sends notification to user's saved contacts
  - Share GPS link: generates shareable link with current GPS coords
- Emergency contacts section: add/remove contacts (name + phone)
- Current GPS display (Alpine.js geolocation)

**Commit:** `feat: SOS screen - configurable alert options, emergency contacts, GPS share`

---

## Phase 7: Google Maps — GCP Setup

### Task 21: GCP project + Maps API key

**Step 1: Create GCP project** (requires Google account)
1. Go to https://console.cloud.google.com
2. Create new project: "Overstrand Adventures"
3. Enable APIs:
   - Maps JavaScript API
   - Directions API
   - Places API (optional, for location search)
4. Create API key: APIs & Services → Credentials → Create Credentials → API Key
5. Restrict key: HTTP referrers → `localhost:*`, `127.0.0.1:*`, `VM_IP:*`
6. Add key to `.env`: `GOOGLE_MAPS_API_KEY=your-key-here`

**Step 2: Verify key works**
```bash
python manage.py shell -c "from django.conf import settings; print(settings.GOOGLE_MAPS_API_KEY[:8])"
```

**Step 3: Commit .env.example update (not the key itself)**
```bash
git add .env.example
git commit -m "docs: document GOOGLE_MAPS_API_KEY in .env.example"
```

---

### Task 22: Admin map drawing tools

**Files:**
- Create: `templates/admin_panel/tours/map_editor.html`
- Create: `static/js/admin-map-editor.js`

- Embed Google Maps in tour edit page with Drawing Library
- DrawingManager for polygon creation → JSON saved to `Tour.polygon`
- Route waypoint editor: click to add, drag to reorder → saves to `MapRouteWaypoint` model
- Preview: show polygon + route on map before saving

**Commit:** `feat: admin map editor - polygon drawing, route waypoint planner`

---

## Phase 8: Push Notifications

### Task 23: Web Push subscription + VAPID keys

**Step 1: Generate VAPID keys**
```bash
python -c "
from cryptography.hazmat.primitives.asymmetric import ec
from base64 import urlsafe_b64encode
import json
key = ec.generate_private_key(ec.SECP256R1())
pub = key.public_key().public_bytes(
    encoding=__import__('cryptography.hazmat.primitives.serialization', fromlist=['Encoding']).Encoding.X962,
    format=__import__('cryptography.hazmat.primitives.serialization', fromlist=['PublicFormat']).PublicFormat.UncompressedPoint
)
print('Public:', urlsafe_b64encode(pub).rstrip(b'=').decode())
"
# Or use: python manage.py generate_vapid_keys (if webpush provides this)
```

**Step 2: Add subscription endpoint** (django-webpush handles this)
```python
# urls.py — include webpush URLs
path('webpush/', include('webpush.urls')),
```

**Step 3: Frontend subscription trigger** (called after user grants notification permission in step 3 of profile setup)

`static/js/push-subscribe.js`:
```javascript
async function subscribeToPush() {
  const reg = await navigator.serviceWorker.ready;
  const vapidKey = document.querySelector('meta[name="vapid-key"]').content;
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: vapidKey,
  });
  await fetch('/webpush/save_information', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
    body: JSON.stringify({ subscription: sub, status_type: 'subscribe', group: 'default' }),
  });
}
```

**Commit:** `feat: Web Push subscription setup with VAPID, service worker push handler`

---

### Task 24: Notification models + Celery task

**Files:**
- Create: `apps/notifications/models.py`
- Create: `apps/notifications/tasks.py`

**Step 1: Write failing test**
```python
@pytest.mark.django_db
def test_send_tour_code_email_task(booking_with_code, mailoutbox):
    from apps.notifications.tasks import send_tour_code_email
    send_tour_code_email(booking_with_code.pk)
    assert len(mailoutbox) == 1
    assert booking_with_code.tour_code in mailoutbox[0].body
```

**Step 2: Write models**

`apps/notifications/models.py`:
```python
class NotificationTag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    colour = models.CharField(max_length=7, default='#6B7280')

class NotificationTemplate(models.Model):
    class TriggerType(models.TextChoices):
        BOOKING_CONFIRMED = 'BOOKING_CONFIRMED'
        RSVP_INVITED = 'RSVP_INVITED'
        PRE_TOUR_24H = 'PRE_TOUR_24H'
        PRE_TOUR_2H = 'PRE_TOUR_2H'
        CUSTOM = 'CUSTOM'
    name = models.CharField(max_length=200)
    title_template = models.CharField(max_length=200)
    body_template = models.TextField()
    trigger_type = models.CharField(max_length=30, choices=TriggerType.choices)
    tags = models.ManyToManyField(NotificationTag, blank=True)
    is_active = models.BooleanField(default=True)

class ScheduledNotification(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING'
        SENT = 'SENT'
        FAILED = 'FAILED'
    class TargetType(models.TextChoices):
        TOUR = 'TOUR'
        BOOKING = 'BOOKING'
        USER = 'USER'
        ALL = 'ALL'
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    target_type = models.CharField(max_length=20, choices=TargetType.choices)
    target_ids = models.JSONField(default=list)
    send_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    tags = models.ManyToManyField(NotificationTag, blank=True)
```

**Step 3: Write Celery tasks**

`apps/notifications/tasks.py`:
```python
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_tour_code_email(booking_id):
    from apps.bookings.models import Booking
    booking = Booking.objects.select_related('user', 'tour').get(pk=booking_id)
    send_mail(
        subject=f'Your tour code for {booking.tour.name}',
        message=f'Hi {booking.user.profile.first_name},\n\n'
                f'Your tour code is: {booking.tour_code}\n\n'
                f'Enter this code in the app to access your itinerary.\n\n'
                f'See you on the trail!\nOverstrand Adventures',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[booking.user.email],
    )

@shared_task
def send_pending_notifications():
    """Celery beat task — runs every minute to dispatch scheduled notifications."""
    from django.utils import timezone
    from .models import ScheduledNotification
    from webpush import send_group_notification
    pending = ScheduledNotification.objects.filter(
        status='PENDING', send_at__lte=timezone.now()
    )
    for notif in pending:
        try:
            _dispatch_notification(notif)
            notif.status = 'SENT'
            notif.sent_at = timezone.now()
        except Exception as e:
            notif.status = 'FAILED'
        notif.save()
```

**Step 4: Run tests + commit**
```bash
pytest apps/notifications/tests/ -v
git add apps/notifications/
git commit -m "feat: push notification models, Celery tasks, tour code email"
```

---

## Phase 9: Admin Panel

### Task 25: Admin panel base layout

**Files:**
- Create: `templates/admin_panel/base.html`
- Create: `apps/dashboard/views.py` (repurpose existing skeleton)
- Create: `apps/dashboard/urls.py`

Key design: Mobile-first, Bootstrap 5 sidebar (collapsible on mobile), top bar with user menu.
DEV MODE banner visible when active.

**Admin sections:**
1. Dashboard — today's stats (tours, bookings, revenue)
2. Tours — CRUD + map editor + itinerary builder
3. Bookings — filter/search, RSVP management, capacity
4. Users — search, view/edit profiles, guide permission toggles
5. Payments — list, manual capture, dev simulate button
6. Notifications — notification manager + scheduler
7. Landing Page — GrapesJS editor + toggle
8. Settings — maintenance mode, SendGrid, payment gateway, SOS options

**Task 26: Tour CRUD + itinerary builder**
- Create tour form with map selector (click to set lat/lng)
- Itinerary builder: drag-drop sortable day/item list (Alpine.js)
- Inline activity item editor with category picker
- Polygon drawing embedded map

**Task 27: User management + guide permissions**
- User list with role filter
- Profile view (health data visible per superuser toggle)
- Guide permission panel: toggles for what guide can see (health info, contact details, financial, personal notes)

**Task 28: Payment management + dev simulate**
- Payment list with status badges
- Manual capture form: amount (ZAR), reference, method (EFT/cash/SnapScan), date, notes
- If DEV_MODE: "Simulate Payment (Paid)" button per pending booking → calls DevSimulateAdapter

**Commit per task:** `feat: admin - [section]`

---

## Phase 10: Landing Page + GrapesJS

### Task 29: Landing page toggle + maintenance mode

**Files:**
- Create: `apps/landing/models.py`
- Create: `apps/landing/middleware.py`
- Create: `templates/landing/maintenance.html`

**Step 1: Write failing test**
```python
@pytest.mark.django_db
def test_maintenance_mode_redirects_non_admin(client, settings_factory):
    settings_factory(maintenance_mode=True)
    response = client.get('/')
    assert response.status_code == 503  # or redirects to /maintenance/

@pytest.mark.django_db
def test_maintenance_mode_allows_admin(admin_client, settings_factory):
    settings_factory(maintenance_mode=True)
    response = admin_client.get('/admin-panel/')
    assert response.status_code == 200
```

**Step 2: Write models**

`apps/landing/models.py`:
```python
class SiteSettings(models.Model):
    maintenance_mode = models.BooleanField(default=False)
    landing_page_enabled = models.BooleanField(default=True)
    maintenance_message = models.TextField(default='We are currently performing maintenance. Back soon!')
    landing_page_html = models.TextField(blank=True)  # GrapesJS output
    landing_page_css = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Site Settings'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
```

**Step 3: Write maintenance middleware**

`apps/landing/middleware.py`:
```python
from django.shortcuts import redirect
from django.http import HttpResponse

class MaintenanceModeMiddleware:
    EXEMPT_PATHS = ['/admin-panel/', '/admin/', '/app/api/', '/accounts/login/']

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(p) for p in self.EXEMPT_PATHS):
            return self.get_response(request)
        if request.user.is_authenticated and request.user.is_staff:
            return self.get_response(request)
        from .models import SiteSettings
        settings = SiteSettings.get()
        if settings.maintenance_mode:
            return HttpResponse(
                render_to_string('landing/maintenance.html', {'message': settings.maintenance_message}),
                status=503
            )
        return self.get_response(request)
```

**Step 4: Commit**
```bash
git add apps/landing/
git commit -m "feat: landing page toggle, maintenance mode middleware"
```

---

### Task 30: GrapesJS landing page editor

**Files:**
- Create: `templates/admin_panel/landing/editor.html`
- Create: `static/vendor/grapesjs/` (CDN or local)
- Create: `apps/landing/views.py` (save HTML/CSS endpoint)

**Step 1: Embed GrapesJS in admin**

```html
<!-- templates/admin_panel/landing/editor.html -->
{% extends "admin_panel/base.html" %}
{% block content %}
<div id="gjs" style="height:calc(100vh - 120px)">
  {{ page.landing_page_html|safe }}
</div>
<script src="https://unpkg.com/grapesjs/dist/grapes.min.js"></script>
<link rel="stylesheet" href="https://unpkg.com/grapesjs/dist/css/grapes.min.css">
<script>
const editor = grapesjs.init({
  container: '#gjs',
  fromElement: true,
  storageManager: false,
  plugins: ['grapesjs-preset-webpage', 'grapesjs-blocks-basic'],
});

document.getElementById('save-btn').addEventListener('click', async () => {
  const html = editor.getHtml();
  const css = editor.getCss();
  await fetch('{% url "landing:save" %}', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '{{ csrf_token }}' },
    body: JSON.stringify({ html, css }),
  });
});
</script>
{% endblock %}
```

**Step 2: Save endpoint**
```python
def save_landing_page(request):
    data = json.loads(request.body)
    site = SiteSettings.get()
    site.landing_page_html = data['html']
    site.landing_page_css = data['css']
    site.save()
    return JsonResponse({'ok': True})
```

**Step 3: Commit**
```bash
git add templates/admin_panel/landing/ apps/landing/
git commit -m "feat: GrapesJS visual landing page editor with save endpoint"
```

---

## Phase 11: NFC + SOS

### Task 31: Web NFC check-in

**Files:**
- Create: `apps/nfc/models.py`
- Create: `apps/nfc/views.py`
- Create: `templates/app/nfc_scan.html`
- Create: `static/js/nfc.js`

**Step 1: Write failing test**
```python
@pytest.mark.django_db
def test_nfc_checkin_creates_record(client, booking_factory):
    booking = booking_factory(status='CONFIRMED')
    client.force_login(booking.user)
    response = client.post(reverse('nfc:checkin'), {
        'tag_id': 'abc123', 'tour_id': booking.tour.pk,
        'lat': '-34.334', 'lng': '19.034'
    })
    assert response.status_code == 200
    from apps.nfc.models import NFCCheckIn
    assert NFCCheckIn.objects.filter(user=booking.user, tag_id='abc123').exists()
```

**Step 2: Write model + view**

```python
class NFCTag(models.Model):
    tag_id = models.CharField(max_length=200, unique=True)
    label = models.CharField(max_length=200)
    tour = models.ForeignKey(Tour, on_delete=models.SET_NULL, null=True)
    purpose = models.CharField(max_length=50, default='CHECKIN')  # CHECKIN | ACTIVITY | PAYMENT

class NFCCheckIn(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tag = models.ForeignKey(NFCTag, on_delete=models.SET_NULL, null=True)
    tag_id = models.CharField(max_length=200)  # raw, in case tag not in DB
    checkin_at = models.DateTimeField(auto_now_add=True)
    lat = models.DecimalField(max_digits=10, decimal_places=7, null=True)
    lng = models.DecimalField(max_digits=10, decimal_places=7, null=True)
```

**Step 3: Write NFC JS** (Android Chrome Web NFC API + graceful fallback)

`static/js/nfc.js`:
```javascript
async function startNFCScan() {
  if (!('NDEFReader' in window)) {
    showQRFallback();
    return;
  }
  const reader = new NDEFReader();
  await reader.scan();
  reader.addEventListener('reading', async ({ serialNumber, message }) => {
    const tagId = serialNumber;
    await fetch('/nfc/checkin/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify({ tag_id: tagId, ...await getGPS() }),
    });
    showCheckInSuccess(tagId);
  });
}

function showQRFallback() {
  document.getElementById('nfc-fallback').style.display = 'block';
  // QR code scanner fallback
}
```

**Step 4: Commit**
```bash
git add apps/nfc/ static/js/nfc.js templates/app/nfc_scan.html
git commit -m "feat: NFC check-in via Web NFC API with QR fallback, NFCCheckIn model"
```

---

### Task 32: SOS feature

**Files:**
- Create: `apps/sos/models.py`
- Create: `apps/sos/views.py`
- Create: `templates/app/sos.html`

**Step 1: Write model**
```python
class SOSSettings(models.Model):
    alert_guide = models.BooleanField(default=True)
    alert_emergency_contacts = models.BooleanField(default=True)
    share_gps_link = models.BooleanField(default=True)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

class SOSEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    triggered_at = models.DateTimeField(auto_now_add=True)
    lat = models.DecimalField(max_digits=10, decimal_places=7, null=True)
    lng = models.DecimalField(max_digits=10, decimal_places=7, null=True)
    guide_notified = models.BooleanField(default=False)
    contacts_notified = models.BooleanField(default=False)
    gps_link_shared = models.BooleanField(default=False)

class EmergencyContact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='emergency_contacts')
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
```

**Step 2: Write SOS trigger view**
- POST `/app/sos/trigger/` → creates SOSEvent → per SOSSettings flags:
  - Guide alert: push notification to guide
  - Emergency contacts: each contact notified (SMS via future integration, for now push/email)
  - GPS link: generate shareable URL with coords

**Step 3: Commit**
```bash
git add apps/sos/
git commit -m "feat: SOS screen - configurable alert options, emergency contacts, GPS share"
```

---

## Phase 12: Backup & Restore

### Task 33: Backup system

**Files:**
- Create: `apps/backups/models.py`
- Create: `apps/backups/management/commands/backup_db.py`
- Create: `apps/backups/views.py`

**Step 1: Write model**
```python
class BackupJob(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING'
        RUNNING = 'RUNNING'
        SUCCESS = 'SUCCESS'
        FAILED = 'FAILED'
    triggered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    triggered_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    file_path = models.CharField(max_length=500, blank=True)
    file_size_bytes = models.BigIntegerField(null=True)
    error_message = models.TextField(blank=True)
```

**Step 2: Write backup command**
```python
# management/commands/backup_db.py
class Command(BaseCommand):
    def handle(self, *args, **options):
        import subprocess, datetime, os
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        path = f'/backups/oa_backup_{ts}.sql'
        os.makedirs('/backups', exist_ok=True)
        subprocess.run([
            'pg_dump', '-h', settings.DATABASES['default']['HOST'],
            '-U', settings.DATABASES['default']['USER'],
            '-d', settings.DATABASES['default']['NAME'],
            '-f', path
        ], check=True, env={**os.environ, 'PGPASSWORD': settings.DATABASES['default']['PASSWORD']})
        self.stdout.write(self.style.SUCCESS(f'Backup saved to {path}'))
```

**Step 3: Celery beat schedule (daily at 2am SAST)**

In settings: schedule `backup_db` command via Celery beat.

**Step 4: Commit**
```bash
git add apps/backups/
git commit -m "feat: backup system - pg_dump command, BackupJob model, admin trigger"
```

---

## Phase 13: Developer Mode System

### Task 34: Dev mode context + simulated workflows

**Files:**
- Create: `apps/accounts/context_processors.py`
- Create: `templates/includes/dev_toolbar.html`

**Step 1: Context processor**

`apps/accounts/context_processors.py`:
```python
from django.conf import settings

def dev_mode(request):
    return {'dev_mode': getattr(settings, 'DEV_MODE', False)}
```

**Step 2: Dev toolbar partial** (shown in all templates when DEV_MODE)

`templates/includes/dev_toolbar.html`:
```html
{% if dev_mode %}
<div class="position-fixed bottom-0 end-0 mb-20 me-3 z-index-9999" style="bottom:80px">
  <div class="dropdown">
    <button class="btn btn-warning btn-sm rounded-pill shadow" data-bs-toggle="dropdown">
      ⚙ DEV
    </button>
    <ul class="dropdown-menu dropdown-menu-end">
      <li><a class="dropdown-item" href="{% url 'accounts:dev_login' %}">Quick Login</a></li>
      <li><a class="dropdown-item" href="{% url 'payments:dev_simulate' %}">Simulate Payment</a></li>
      <li><a class="dropdown-item" href="{% url 'nfc:dev_simulate' %}">Simulate NFC Tap</a></li>
      <li><a class="dropdown-item" href="{% url 'notifications:dev_push' %}">Test Push</a></li>
      <li><hr class="dropdown-divider"></li>
      <li><small class="dropdown-item-text text-muted">DEV MODE ACTIVE</small></li>
    </ul>
  </div>
</div>
{% endif %}
```

**Step 3: Commit**
```bash
git add apps/accounts/context_processors.py templates/includes/dev_toolbar.html
git commit -m "feat: dev mode context processor and dev toolbar overlay"
```

---

## Phase 14: Tour Code Word Seeding

### Task 35: Seed Overberg/nature word list

**Files:**
- Create: `apps/tours/management/commands/seed_tour_codes.py`

**Step 1: Write seed command**

`apps/tours/management/commands/seed_tour_codes.py`:
```python
from django.core.management.base import BaseCommand
from apps.tours.models import TourCodeWord

OVERBERG_WORDS = [
    'fynbos', 'pelican', 'milkwood', 'protea', 'renosterveld', 'klipspringer',
    'bontebok', 'greenbul', 'kogelberg', 'kleinmond', 'hermanus', 'walker',
    'whale', 'lagoon', 'dune', 'estuary', 'sugarbird', 'agulhas',
    'overstrand', 'palmiet', 'baboon', 'boulders', 'safari', 'mountain',
    'sunrise', 'trailhead', 'rockpool', 'saltwater', 'granite', 'bluegum',
    'cape', 'peninsula', 'anchor', 'tidal', 'coral', 'compass',
    'fernwood', 'beacon', 'crest', 'summit', 'floodplain', 'lagoonside',
    'strandloper', 'otter', 'egret', 'kingfisher', 'heron', 'ibis',
    'geranium', 'orchid', 'buchu', 'rooibos', 'wisteria', 'honeybush',
]

class Command(BaseCommand):
    help = 'Seed Overberg/nature themed tour code words'

    def handle(self, *args, **options):
        created = 0
        for word in OVERBERG_WORDS:
            _, c = TourCodeWord.objects.get_or_create(word=word)
            if c:
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Seeded {created} new tour code words ({len(OVERBERG_WORDS)} total)'))
```

**Step 2: Run seed**
```bash
python manage.py seed_tour_codes
python manage.py seed_categories
```

**Step 3: Commit**
```bash
git add apps/tours/management/commands/seed_tour_codes.py
git commit -m "feat: seed 55 Overberg/nature tour code words"
```

---

## Phase 15: PWA Hardening + Production

### Task 36: Final PWA hardening checklist

**Files:**
- Create: `templates/app/offline.html`
- Modify: `static/js/service-worker.js`

**Checklist:**
- [ ] Service worker caches home, itinerary, profile, SOS pages
- [ ] Offline fallback page designed and cached
- [ ] Push notification icon assets (192px, 72px badge)
- [ ] PWA icons (192px, 512px) — client to provide branded icons
- [ ] `manifest.json` screenshots field for install prompt
- [ ] HTTPS or localhost only (Web Push + NFC require secure context)
- [ ] Background sync for SOS events queued when offline
- [ ] CSRF token included in HTMX requests (`hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'`)
- [ ] `SECURE_HSTS_SECONDS`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE` in production settings

---

## Full Seed Command Sequence (first run)

Run in this order on fresh database:
```bash
python manage.py migrate
python manage.py seed_categories
python manage.py seed_tour_codes
python manage.py shell -c "
from apps.landing.models import SiteSettings
from django.contrib.sites.models import Site
Site.objects.update_or_create(pk=1, defaults={'domain': 'localhost', 'name': 'Overstrand Adventures'})
SiteSettings.objects.get_or_create(pk=1)
print('Site settings initialised')
"
python manage.py createsuperuser
```

---

## Test Coverage Targets

| App | Target | Key tests |
|---|---|---|
| accounts | 85% | OTP flow, profile wizard, social auth |
| tours | 80% | Tour CRUD, code generation, capacity |
| bookings | 80% | RSVP, capacity enforcement, confirmation |
| payments | 90% | Adapter pattern, dev simulate, manual capture |
| notifications | 80% | Email send, push dispatch, scheduling |
| sos | 75% | Event creation, configurable alerts |
| nfc | 75% | Check-in record, tag matching |

Run full suite:
```bash
pytest --cov=apps --cov-report=term-missing
```
Expected: 80%+ overall.

---

## Execution Order Summary

| Phase | Tasks | Deliverable |
|---|---|---|
| 1 | 1–4 | Docker stacks, SSH guide, Dockerfile |
| 2 | 5–6 | Django restructure, all apps scaffolded |
| 3 | 7–10 | Full auth system + 5-step profile wizard |
| 4 | 11–12 | Tours, categories, itinerary items |
| 5 | 13–14 | Bookings, payment adapter |
| 6 | 15–20 | All 5 PWA screens pixel-perfect |
| 7 | 21–22 | Google Maps + admin map editor |
| 8 | 23–24 | Push notifications + Celery tasks |
| 9 | 25–28 | Admin panel all sections |
| 10 | 29–30 | Landing page + GrapesJS |
| 11 | 31–32 | NFC check-in + SOS |
| 12 | 33 | Backup/restore |
| 13 | 34 | Dev mode toolbar |
| 14 | 35 | Seed commands |
| 15 | 36 | PWA hardening |
