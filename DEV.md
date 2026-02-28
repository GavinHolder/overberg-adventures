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
