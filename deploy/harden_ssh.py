"""Apply SSH hardening and verify state on the OA VM."""
import paramiko
import os

VM_IP = "10.0.0.14"
VM_USER = "gavin"
VM_PASS = "gavin"
KEY_PATH = os.path.expanduser("~/.ssh/oa_vm")

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VM_IP, username=VM_USER, key_filename=KEY_PATH, timeout=10)
print("Connected via key")

# Check current SSH config
_, o, _ = client.exec_command(
    "grep -E 'PasswordAuthentication|PubkeyAuthentication|KbdInteractive' /etc/ssh/sshd_config"
)
print("\nCurrent sshd_config relevant lines:")
print(o.read().decode())

# Apply hardening via sudo -S bash
print("Applying SSH hardening...")
SCRIPT = (
    'sed -i "s/^#*PasswordAuthentication.*/PasswordAuthentication no/" /etc/ssh/sshd_config\n'
    'sed -i "s/^#*PubkeyAuthentication.*/PubkeyAuthentication yes/" /etc/ssh/sshd_config\n'
    'sed -i "s/^#*KbdInteractiveAuthentication.*/KbdInteractiveAuthentication no/" /etc/ssh/sshd_config\n'
    'grep -qxF "PasswordAuthentication no" /etc/ssh/sshd_config'
    ' || echo "PasswordAuthentication no" >> /etc/ssh/sshd_config\n'
    'sshd -t && echo "Config valid"\n'
    'systemctl restart sshd && echo "sshd restarted OK"\n'
)

stdin, stdout, stderr = client.exec_command("sudo -S bash -s")
stdin.write(VM_PASS + "\n")
stdin.write(SCRIPT)
stdin.channel.shutdown_write()

out = stdout.read().decode().strip()
err = stderr.read().decode().strip()
for line in out.splitlines():
    print(line)
err_lines = [
    l for l in err.splitlines()
    if "[sudo]" not in l and "password for" not in l.lower()
]
for line in err_lines:
    print("ERR:", line)

client.close()
print("\nDone. Test with: ssh -i ~/.ssh/oa_vm gavin@10.0.0.14 echo OK")
