"""
Bootstrap script for OA VM — Phase 2 (deploy stacks + harden SSH).
Assumes SSH key is already installed (Phase 1 complete).

Usage: python deploy/bootstrap_vm.py
"""
import paramiko
import os
import time

VM_IP = "10.0.0.14"
VM_USER = "gavin"
VM_PASS = "gavin"
KEY_PATH = os.path.expanduser("~/.ssh/oa_vm")


def run_script(client, script, desc=None):
    """
    Run a bash script as root via 'echo PASS | sudo -S bash -s'.
    The script is fed to bash's stdin after the sudo password.
    """
    if desc:
        print(f"\n  [{desc}]")
    stdin, stdout, stderr = client.exec_command("sudo -S bash -s")
    # sudo -S reads password from stdin first line, then bash reads the rest
    stdin.write(VM_PASS + "\n")
    stdin.write(script)
    stdin.channel.shutdown_write()
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    code = stdout.channel.recv_exit_status()
    # Filter sudo password prompt from stderr
    err_lines = [l for l in err.splitlines()
                 if "[sudo]" not in l and "password for" not in l.lower()]
    if out:
        for line in out.splitlines():
            print(f"    {line}")
    if err_lines:
        for line in err_lines:
            print(f"    ERR: {line}")
    return code


def run(client, cmd, desc=None):
    """Run a plain command (no sudo) via SSH."""
    if desc:
        print(f"  > {desc}")
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    code = stdout.channel.recv_exit_status()
    if out:
        print(f"    {out[:400]}")
    if err and code != 0:
        print(f"    ERR: {err[:200]}")
    return code, out, err


def main():
    print("=" * 60)
    print(f"OA VM Deploy — {VM_IP}")
    print("=" * 60)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Connect with key (already installed)
    print(f"\nConnecting with SSH key...")
    try:
        client.connect(VM_IP, username=VM_USER, key_filename=KEY_PATH, timeout=10)
        print("  Connected via key auth.")
    except Exception:
        print("  Key auth failed, falling back to password...")
        client.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=10)
        print("  Connected via password.")

    # --- Deploy all stacks ---
    print("\n[1/3] Deploying Traefik, Portainer, Redis stacks...")
    code = run_script(client, """
set -e
# Ensure network exists
docker network create traefik_net 2>/dev/null || echo "traefik_net already exists"

# Traefik
echo "--- Starting Traefik ---"
docker compose -f /home/gavin/overberg-adventures/deploy/traefik/docker-compose.yml up -d
docker ps --filter name=traefik --format "traefik: {{.Status}}"

# Portainer
echo "--- Starting Portainer ---"
docker compose -f /home/gavin/overberg-adventures/deploy/portainer/docker-compose.yml up -d
docker ps --filter name=portainer --format "portainer: {{.Status}}"

# Redis
echo "--- Starting Redis ---"
docker compose -f /home/gavin/overberg-adventures/deploy/redis/docker-compose.yml up -d
docker ps --filter name=redis --format "redis: {{.Status}}"

echo "--- All stacks up ---"
docker ps --format "{{.Names}}  {{.Status}}"
""", desc="starting stacks")

    if code != 0:
        print("  WARNING: stack deploy had errors (see above)")
    else:
        print("  Stacks deployed.")

    # --- Harden SSH ---
    print("\n[2/3] Hardening SSH (key-only auth)...")
    code = run_script(client, r"""
set -e
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#*KbdInteractiveAuthentication.*/KbdInteractiveAuthentication no/' /etc/ssh/sshd_config
# Ensure line exists if not already
grep -qxF 'PasswordAuthentication no' /etc/ssh/sshd_config \
  || echo 'PasswordAuthentication no' >> /etc/ssh/sshd_config
# Validate config before restarting
sshd -t && systemctl restart sshd
echo "SSH hardened OK"
""", desc="SSH hardening")

    if code != 0:
        print("  WARNING: SSH hardening had errors — check manually")
    else:
        print("  SSH password auth disabled.")

    # Small wait for sshd to restart
    time.sleep(2)

    # --- Verify key auth still works ---
    print("\n[3/3] Verifying key auth still works...")
    client2 = paramiko.SSHClient()
    client2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client2.connect(VM_IP, username=VM_USER, key_filename=KEY_PATH, timeout=10)
        run(client2, "docker ps --format '{{.Names}}  {{.Status}}'", desc="container status")
        client2.close()
        print("  Key auth confirmed working after SSH hardening.")
    except Exception as e:
        print(f"  WARNING: Could not reconnect with key: {e}")
        print("  Check VM manually: ssh -i ~/.ssh/oa_vm gavin@10.0.0.14")

    client.close()

    print("\n" + "=" * 60)
    print("DEPLOY COMPLETE")
    print("=" * 60)
    print(f"\n  Portainer:     http://10.0.0.14:9000")
    print(f"  Traefik dash:  http://10.0.0.14:8080  (or SSH tunnel)")
    print(f"  App endpoint:  http://10.0.0.14/")
    print(f"\n  SSH access:    ssh -i ~/.ssh/oa_vm gavin@10.0.0.14")
    print(f"\nNEXT STEPS:")
    print("  1. Open http://10.0.0.14:9000 — set Portainer admin password NOW (5 min timeout)")
    print("  2. Stacks > Add stack > Repository")
    print("     URL:     https://github.com/GavinHolder/overberg-adventures")
    print("     Compose: deploy/app/docker-compose.yml")
    print("     Add your .env variables, then Deploy")
    print(f"\n  Remote access (external): forward port 9000 on your router -> 10.0.0.14:9000")
    print(f"  Then access Portainer at: http://105.184.248.55:9000  (update when IP changes)")


if __name__ == "__main__":
    main()
