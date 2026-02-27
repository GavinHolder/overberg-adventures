"""
Django settings for overberg_adventures project.
"""

from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

SECRET_KEY = config('DJANGO_SECRET_KEY')

DEBUG = config('DEBUG', default=False, cast=bool)

# DEV_MODE is ONLY active when DEBUG is also True
DEV_MODE = config('DEV_MODE', default=False, cast=bool) and DEBUG

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

SITE_ID = config('SITE_ID', default=1, cast=int)

# ---------------------------------------------------------------------------
# Installed apps
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    # Django builtins
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

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Must be after SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    # Activates once landing app models are built:
    # 'apps.landing.middleware.MaintenanceModeMiddleware',
]

# ---------------------------------------------------------------------------
# URLs / WSGI
# ---------------------------------------------------------------------------

ROOT_URLCONF = 'overberg_adventures.urls'

WSGI_APPLICATION = 'overberg_adventures.wsgi.application'

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.accounts.context_processors.dev_mode',
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

_db_engine = config('DB_ENGINE', default='django.db.backends.sqlite3')

if _db_engine == 'django.db.backends.sqlite3':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / config('DB_NAME', default='db.sqlite3'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': _db_engine,
            'NAME': config('DB_NAME', default='overberg_adventures'),
            'USER': config('DB_USER', default=''),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

LOGIN_REDIRECT_URL = '/app/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

_sendgrid_api_key = config('SENDGRID_API_KEY', default='')

if _sendgrid_api_key:
    EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

ANYMAIL = {
    'SENDGRID_API_KEY': _sendgrid_api_key,
}

DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@localhost')

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ---------------------------------------------------------------------------
# Media files
# ---------------------------------------------------------------------------

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Johannesburg'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Default primary key
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------

CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# ---------------------------------------------------------------------------
# Google Maps
# ---------------------------------------------------------------------------

GOOGLE_MAPS_API_KEY = config('GOOGLE_MAPS_API_KEY', default='')

# ---------------------------------------------------------------------------
# Web Push (VAPID)
# ---------------------------------------------------------------------------

WEBPUSH_SETTINGS = {
    'VAPID_PUBLIC_KEY': config('VAPID_PUBLIC_KEY', default=''),
    'VAPID_PRIVATE_KEY': config('VAPID_PRIVATE_KEY', default=''),
    'VAPID_ADMIN_EMAIL': config('VAPID_ADMIN_EMAIL', default='dev@localhost'),
}

# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

PAYMENT_GATEWAY = config('PAYMENT_GATEWAY', default='manual')

# ---------------------------------------------------------------------------
# Debug toolbar (only when DEBUG=True)
# ---------------------------------------------------------------------------

if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
    INTERNAL_IPS = ['127.0.0.1']
