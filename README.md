```markdown
# pythonfirewall (Raspberry Pi 5 — Kali Linux)

A small Flask web dashboard intended for Raspberry Pi 5 running Kali Linux.
It listens on 0.0.0.0 so other devices on your LAN can access it (PlayStation, Xbox, mobile, PC).

Important:
- Change ADMIN_PASS before exposing to networks.
- Do NOT enable rule modification unless you restrict sudo and understand the risks.

Quick local setup
1. Create a dedicated user (recommended):
   sudo adduser --disabled-login --gecos "PythonFirewall" pyfw

2. Install runtime and tools:
   sudo apt update
   sudo apt install -y python3 python3-venv python3-pip git nginx certbot

3. Clone repo and install:
   git clone <your-repo-url> pythonfirewall
   cd pythonfirewall
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

4. Configure environment variables (example):
   export ADMIN_USER="admin"
   export ADMIN_PASS="a_very_strong_password"
   export PORT="8080"
   export ALLOW_FIREWALL_CONTROL="false"
   export USE_NFT="true"

   For systemd, put these into /etc/default/pythonfirewall (example below)

5. Run for testing:
   source venv/bin/activate
   python app.py
   Visit http://<pi-ip>:8080

Systemd unit example
- Copy pythonfirewall.service to /etc/systemd/system/pythonfirewall.service, edit paths/user as needed.
- Reload and enable:
  sudo systemctl daemon-reload
  sudo systemctl enable --now pythonfirewall

Sudoers (visudo snippet)
- To allow only nft read and specific commands for the pyfw user, edit sudoers with visudo and add:
  pyfw ALL=(root) NOPASSWD: /usr/sbin/nft, /usr/sbin/nft --version

  If you use iptables instead:
  pyfw ALL=(root) NOPASSWD: /sbin/iptables, /sbin/iptables-save, /sbin/iptables-restore

  IMPORTANT: avoid giving broad or shell-wrapped privileges. Test carefully.

Nginx reverse-proxy + Let's Encrypt (brief)
- Basic nginx site (adjust server_name and proxy_pass):
  /etc/nginx/sites-available/pythonfirewall
  server {
      listen 80;
      server_name example.yourdomain.com;

      location / {
          proxy_pass http://127.0.0.1:8080;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
      }
  }

- Enable and reload nginx:
  sudo ln -s /etc/nginx/sites-available/pythonfirewall /etc/nginx/sites-enabled/
  sudo nginx -t && sudo systemctl reload nginx

- Obtain TLS cert with certbot:
  sudo certbot --nginx -d example.yourdomain.com

Editors: nano and Visual Studio Code
- Nano:
  sudo nano /etc/default/pythonfirewall
  sudo nano /etc/systemd/system/pythonfirewall.service
  sudo nano app.py

- Visual Studio Code (Remote-SSH recommended):
  - Install "Remote - SSH" on your workstation VS Code.
  - Connect: Remote-SSH to pyfw@<pi-ip>, open folder and edit.

Push to GitHub (commands)
1. Using the GitHub website:
   - Create repository 'pythonfirewall' on GitHub under your account.
   - Then run:
     git init
     git add .
     git commit -m "Initial pythonfirewall"
     git branch -M main
     git remote add origin git@github.com:<yourusername>/pythonfirewall.git
     git push -u origin main

2. Using the GitHub CLI (gh):
   - Make sure you are logged in: gh auth login
   - Run the create_repo.sh script included in this repo:
     chmod +x create_repo.sh
     ./create_repo.sh

SSH key quick setup (Kali -> GitHub)
- Generate key:
  ssh-keygen -t ed25519 -C "your_email@example.com"
- Add key to GitHub account (copy contents of ~/.ssh/id_ed25519.pub to GitHub > Settings > SSH and GPG keys)
- Test:
  ssh -T git@github.com

Security checklist before exposing to the internet
- Change ADMIN_PASS to a long random secret.
- Use HTTPS (reverse proxy with nginx + Let's Encrypt or Cloudflare Tunnel).
- Prefer VPN or reverse SSH tunnel instead of direct port forwarding.
- Minimize sudo privileges for the web user; prefer read-only views unless necessary.

If you want, I can:
- produce a completed visudo snippet tailored to nft or iptables,
- give the exact nginx site file populated with your domain,
- or generate the prefilled systemd file and a one-line install script for the Pi.
```
