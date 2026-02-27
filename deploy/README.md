# Deployment Architecture

The infrastructure is split into 4 independent Docker Compose stacks. Each stack is deployed separately; no stack depends on another at the Compose level. All stacks join the shared `traefik_net` Docker bridge network for inter-container communication and Traefik routing.

---

## Stack Overview

| Stack | Directory | Purpose | Port(s) |
|-------|-----------|---------|---------|
| **Traefik** | `deploy/traefik/` | Reverse proxy, TLS termination, routing | 80, 443, 8080 (dashboard) |
| **Portainer** | `deploy/portainer/` | Docker management UI | 9000 |
| **Redis** | `deploy/redis/` | Celery broker + cache | (internal only) |
| **App** | `deploy/app/` | Django web, Celery worker, Celery Beat, PostgreSQL | (via Traefik) |

---

## Network Design

Traefik creates the `traefik_net` bridge network when its stack is first deployed. All other stacks declare `traefik_net` as `external: true`, meaning they join it without recreating it. This is why **Traefik must be deployed first**.

```
traefik_net (bridge)
├── traefik        (creates + owns the network)
├── portainer      (joins as external)
├── redis          (joins as external)
├── oa_web         (joins as external)
├── oa_db          (joins as external)
├── oa_celery      (joins as external)
└── oa_celery_beat (joins as external)
```

---

## Deployment Order

Deploy stacks in this exact order:

```
1. deploy/traefik/     (FIRST — creates traefik_net)
2. deploy/portainer/   (second — joins traefik_net)
3. deploy/redis/       (third — joins traefik_net)
4. deploy/app/         (last — client deploys via Portainer UI)
```

Detailed deployment steps: see `deploy/SSH_SETUP.md`.

---

## App Stack Deployment (Client Responsibility)

The app stack (`deploy/app/docker-compose.yml`) is deployed and managed by the client using the Portainer UI. The workflow is:

1. Client logs into Portainer at `http://YOUR_VM_IP:9000`
2. Go to **Stacks** > **Add stack**
3. Choose **Repository** and enter the GitHub repo URL
4. Set the Compose file path to `deploy/app/docker-compose.yml`
5. Add environment variables (see `.env.example` in the repo root)
6. Deploy the stack

Portainer will pull the image from GitHub Container Registry (`ghcr.io`) and start all services. To update, the client re-deploys the stack or uses Portainer's webhook integration for automatic updates on new image pushes.

**Note:** Replace `YOUR_GITHUB_ORG` in `deploy/app/docker-compose.yml` with the actual GitHub organisation once the repo is created.

---

## Key Files

| File | Purpose |
|------|---------|
| `deploy/traefik/docker-compose.yml` | Traefik stack |
| `deploy/traefik/traefik.yml` | Traefik static configuration |
| `deploy/portainer/docker-compose.yml` | Portainer stack |
| `deploy/redis/docker-compose.yml` | Redis stack |
| `deploy/app/docker-compose.yml` | App stack (client-managed) |
| `Dockerfile` | Application image build |
| `.env.example` | Environment variable template |
| `deploy/SSH_SETUP.md` | Full SSH and VM setup guide |
