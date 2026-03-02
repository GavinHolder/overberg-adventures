# Overstrand Adventures — Developer Access

## Dev Server

Start the server:
```bash
python manage.py runserver 8000
```

| URL | Purpose |
|-----|---------|
| `http://127.0.0.1:8000/` | Guest PWA (home screen) |
| `http://127.0.0.1:8000/guide/` | Guide Dashboard |
| `http://127.0.0.1:8000/admin/` | Django Admin |
| `http://127.0.0.1:8000/accounts/login/` | Login page |

---

## Accounts

### Dev Quick Login (no OTP)
On the login page there is a **"Dev Login (skip OTP)"** button at the bottom.

| Field | Value |
|-------|-------|
| Email | `dev@overstrand.local` |
| Role | ADMIN (full access to everything) |

> Only visible when `DEV_MODE=True` in `.env`

### Admin Account

| Field | Value |
|-------|-------|
| Email | `admin@overstrand.local` |
| Password | `admin123` |
| Role | ADMIN / Superuser |

---

## Tour Codes

Enter these on the home screen (/) to join a tour.

| Tour | Code | Status |
|------|------|--------|
| Kogelberg Coastal Walk | `elgin` | Active |

### Unused codes (to create new tours)
`agulhas` · `anchor` · `baboon` · `beacon` · `bluegum` · `bontebok` · `buchu` · `canyon` · `compass` · `crest`

Full list managed via Django Admin → Tour Code Words.

---

## DEV MODE Features

Activated by `DEV_MODE=True` in `.env` (only works when `DEBUG=True`).

| Feature | Where |
|---------|-------|
| Orange banner "DEV MODE — OTP bypassed" | All PWA pages |
| Red banner "DEV MODE — not for production" | Guide Dashboard |
| Dev Login button (skip OTP) | `/accounts/login/` |
| DEV MODE section on Profile page | `/accounts/profile/` |
| Payment simulation (Phase 10, not yet built) | Booking flow |

---

## Guide Dashboard

URL: `http://127.0.0.1:8000/guide/`

Requires role `GUIDE`, `OPERATOR`, or `ADMIN` (or `is_staff=True`).

| Tab | URL |
|-----|-----|
| Tours | `/guide/tours/` |
| Activities | `/guide/activities/` |
| Guests | `/guide/guests/` |
| Guides | `/guide/guides/` |

---

## Django Admin

URL: `http://127.0.0.1:8000/admin/`
Login: `admin@overstrand.local` / `admin123`

Useful for managing tour code words, users, SOS config, activity categories.

---

## Environment

Key `.env` variables for dev:

```env
DEV_MODE=True
DEBUG=True
SECRET_KEY=...
DATABASE_URL=sqlite:///db.sqlite3
```

---

## Social Auth (Google OAuth)

Social login is managed via the backend dashboard at `/guide/settings/social-auth/` (staff login required).

### Setup Steps

1. **Create a Google OAuth app:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   - Create an OAuth 2.0 Client ID (Web application type)
   - Add authorised redirect URI: `http://localhost:8000/accounts/google/login/callback/` (dev)
   - For production: `https://yourdomain.com/accounts/google/login/callback/`

2. **Configure in backend dashboard:**
   - Log in as a staff user
   - Go to `/guide/settings/social-auth/`
   - Enter the Client ID and Client Secret for Google
   - Toggle the provider to **Enabled**
   - The Google button will appear on the login page immediately

3. **Alternative — use env vars (for dev/CI):**
   ```
   GOOGLE_CLIENT_ID=your_client_id_here
   GOOGLE_SECRET=your_client_secret_here
   ```
   Set `enabled=True` on the `SocialAuthProvider` record in the Django admin or via shell.

### Django Site ID

Make sure `SITE_ID=1` in your `.env`. The sites framework must have a `Site` record with `pk=1`.
To verify: `python manage.py shell -c "from django.contrib.sites.models import Site; print(list(Site.objects.all()))"`

If missing: `python manage.py shell -c "from django.contrib.sites.models import Site; Site.objects.get_or_create(pk=1, defaults={'domain': 'localhost:8000', 'name': 'localhost'})"`
