# SSH Setup & VM Deployment Guide

This guide walks through setting up passwordless SSH access to the production VM and deploying the Docker infrastructure stacks.

---

## 1. Generate SSH Key on Dev Machine

Run this on your local machine (Windows PowerShell, WSL, or macOS/Linux terminal):

```bash
ssh-keygen -t ed25519 -C "overberg-adventures-deploy" -f ~/.ssh/oa_vm
```

When prompted for a passphrase, either set one (recommended) or leave blank for fully automated access.

This creates two files:
- `~/.ssh/oa_vm` — private key (never share this)
- `~/.ssh/oa_vm.pub` — public key (copied to server)

---

## 2. Copy Public Key to VM

Replace `YOUR_VM_IP` with the actual VM IP address and `YOUR_VM_USER` with your VM username (typically `ubuntu` or `root`):

```bash
ssh-copy-id -i ~/.ssh/oa_vm.pub YOUR_VM_USER@YOUR_VM_IP
```

If `ssh-copy-id` is not available (Windows without WSL), copy manually:

```bash
# First login with password
ssh YOUR_VM_USER@YOUR_VM_IP

# On the VM, append your public key
mkdir -p ~/.ssh
echo "PASTE_YOUR_PUBLIC_KEY_CONTENT_HERE" >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
exit
```

---

## 3. Configure ~/.ssh/config

Add this block to `~/.ssh/config` (create the file if it doesn't exist):

```
Host oa-vm
    HostName YOUR_VM_IP
    User YOUR_VM_USER
    IdentityFile ~/.ssh/oa_vm
    IdentitiesOnly yes
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

---

## 4. Test Passwordless Access

```bash
ssh oa-vm
```

You should connect without being prompted for a password. If it still asks for a password, check:
- The public key was appended to `~/.ssh/authorized_keys` on the VM
- File permissions on the VM: `~/.ssh` is 700, `authorized_keys` is 600
- The `IdentityFile` path in `~/.ssh/config` is correct

---

## 5. Disable Password Authentication on VM

Once passwordless SSH is confirmed working, harden the VM by disabling password auth.

On the VM:

```bash
sudo nano /etc/ssh/sshd_config
```

Set (or add) these lines:

```
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
```

Restart SSH daemon:

```bash
sudo systemctl restart sshd
```

**Do not close your current SSH session until you confirm you can open a new session successfully.**

---

## 6. Install Docker on VM

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

Log out and back in so the group change takes effect:

```bash
exit
ssh oa-vm
docker version  # should work without sudo
```

---

## 7. Copy Infrastructure Files to VM

From your local machine, copy the deploy folder to the VM:

```bash
scp -r deploy/ oa-vm:~/overberg-adventures/
```

Or clone the GitHub repo on the VM once it is set up:

```bash
ssh oa-vm
git clone https://github.com/YOUR_GITHUB_ORG/overberg-adventures.git
cd overberg-adventures
```

---

## 8. Deploy Stacks in Correct Order

**Order is critical.** Traefik must be deployed first because it creates the `traefik_net` network that all other stacks join as external.

### Stack 1: Traefik (creates traefik_net)

```bash
cd ~/overberg-adventures/deploy/traefik
docker compose up -d
```

Traefik dashboard is bound to localhost only. Access it via SSH tunnel (see "Accessing Services via SSH Tunnel" below).

### Stack 2: Portainer

```bash
cd ~/overberg-adventures/deploy/portainer
docker compose up -d
```

Portainer is bound to localhost only. Access it via SSH tunnel (see "Accessing Services via SSH Tunnel" below).
Create your admin account on first access (do this immediately — Portainer times out the initial setup).

### Stack 3: Redis

```bash
cd ~/overberg-adventures/deploy/redis
docker compose up -d
```

Verify Redis is healthy:

```bash
docker exec redis redis-cli ping
# Expected output: PONG
```

### Stack 4: App (client deploys via Portainer UI)

The app stack is deployed manually by the client from GitHub via the Portainer UI. See `deploy/README.md` for instructions on how the client does this.

---

## 9. Verify All Stacks Running

```bash
docker ps
```

Expected containers: `traefik`, `portainer`, `redis`

Check network:

```bash
docker network inspect traefik_net
```

All containers should appear under the `Containers` section.

---

## Troubleshooting

**Traefik not starting:** Check `./traefik.yml` is present in `deploy/traefik/` and is valid YAML.

**Network not found errors on Portainer/Redis:** Deploy Traefik first — it creates `traefik_net`.

**Portainer can't connect to Docker:** Ensure `/var/run/docker.sock` is accessible. The VM user must be in the `docker` group.

**Redis healthcheck failing:** Give it 30 seconds on first start. Check logs with `docker logs redis`.

---

## Accessing Services via SSH Tunnel

Since Portainer (9000) and Traefik dashboard (8080) are bound to localhost only, they are not directly reachable from the internet. Access them by forwarding the port over SSH:

```bash
# Portainer
ssh -L 9000:localhost:9000 oa-vm
# Then open: http://localhost:9000

# Traefik dashboard
ssh -L 8080:localhost:8080 oa-vm
# Then open: http://localhost:8080
```

Keep the SSH session open while using the UI. Open a second terminal for other VM commands.
