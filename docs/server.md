# Server Info

## VM
- **Local IP:** 10.0.0.14
- **External IP:** 105.184.248.55 (dynamic — update bookmark when it changes)
- **User:** gavin
- **Password:** gavin (SSH password auth disabled — key auth only)
- **SSH key:** `~/.ssh/oa_vm` (ed25519)
- **SSH alias:** `ssh oa-vm`

## Portainer
- **Local:** http://10.0.0.14:9000
- **Remote:** http://105.184.248.55:9000 (requires port 9000 forwarded on router)
- **Login:** admin / B3rryP0rtal@5

## Traefik Dashboard
- **URL:** http://10.0.0.14:8080 (LAN only)

## Git / GitHub
- **Repo:** https://github.com/GavinHolder/overberg-adventures
- **Token:** (stored locally — do not commit)
- **Container Registry:** ghcr.io/gavinholder/overberg-adventures:latest

## Database
- **Password:** Overberg@2026!
- **User:** oa_user
- **DB:** overberg_adventures
- **Host:** db (internal Docker network)

## App URLs
| URL | Purpose |
|-----|---------|
| http://10.0.0.14/ | App home |
| http://10.0.0.14/accounts/login/ | Login page (Google OAuth + dev buttons) |
| http://10.0.0.14/dashboard/ | Guide portal |
| http://10.0.0.14/backend/ | Custom admin panel |
| http://10.0.0.14/admin/ | Django default admin |

## Google OAuth
- **Client ID:** (stored in DB — backend → Social Login Providers)
- **Client Secret:** (stored in DB — backend → Social Login Providers)
- **Callback URL:** http://10.0.0.14/accounts/google/login/callback/
- **Stored in:** DB via `SocialAuthProvider` model (backend → Social Login Providers)

## Encryption Key
- **FIELD_ENCRYPTION_KEY:** SoxcUesklAZvNRZalSZF6GOKJ_uIuPuD7RnlkN7tgxE=
- **DJANGO_SECRET_KEY:** RHvdYydBStvs_279W083Gapltm7Q5Gt2xxWqT52I1LJT8ZJTJTD1fcywTxkHzZ0hfLw

## Redeploy Command
```bash
ssh oa-vm "cd ~/overberg-adventures && git pull && docker compose -f deploy/app/docker-compose.yml --env-file .env up --build --force-recreate -d"
```

## Docker Stacks
| Stack | Compose file |
|-------|-------------|
| Traefik | `~/overberg-adventures/deploy/traefik/docker-compose.yml` |
| Portainer | `~/overberg-adventures/deploy/portainer/docker-compose.yml` |
| Redis | `~/overberg-adventures/deploy/redis/docker-compose.yml` |
| App | `~/overberg-adventures/deploy/app/docker-compose.yml` |

## .env Location on VM
`~/overberg-adventures/.env`
