```markdown
# pythonfirewall (Raspberry Pi 3B+ — Kali Linux)

A small Flask web dashboard intended for Raspberry Pi 3B+ running Kali Linux.
It listens on 0.0.0.0 so other devices on your LAN can access it (PlayStation 5, Xbox, mobile, PC).
Includes integrated support for Squid proxy, Unbound DNS, UFW firewall, and Fail2ban intrusion prevention.

Important:
- Change ADMIN_PASS before exposing to networks.
- Do NOT enable rule modification unless you restrict sudo and understand the risks.

Quick local setup
1. Create a dedicated user (recommended):
   sudo adduser --disabled-login --gecos "PythonFirewall" pyfw

2. Install runtime and tools:
   sudo apt update
   sudo apt install -y python3 python3-venv python3-pip git nginx certbot squid unbound ufw fail2ban

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

## Integrated Components Setup

### Squid Proxy Configuration
Squid provides HTTP/HTTPS caching and proxy services, useful for reducing bandwidth and improving PS5 download speeds.

1. Copy the provided squid.conf to /etc/squid/squid.conf
2. Configure PS5 to use proxy: Settings > Network > Set Up Internet Connection > Custom > Proxy Server
3. Use Raspberry Pi IP address and port 3128
4. Start and enable:
   sudo systemctl enable --now squid
   sudo systemctl status squid

### Unbound DNS Configuration
Unbound provides secure, fast DNS resolution with DNSSEC validation.

1. Copy the provided unbound.conf to /etc/unbound/unbound.conf.d/custom.conf
2. Configure devices to use RPi as DNS server (use RPi's IP address)
3. Start and enable:
   sudo systemctl enable --now unbound
   sudo systemctl status unbound

### UFW Firewall Configuration
UFW (Uncomplicated Firewall) provides simple firewall management with PS5-optimized rules.

1. Enable UFW:
   sudo ufw enable
2. Apply PS5 rules using the provided script:
   sudo bash ufw-ps5-setup.sh
3. Check status:
   sudo ufw status verbose

Key PS5 ports:
- TCP 80, 443 (HTTP/HTTPS)
- TCP 3478-3480 (PSN)
- UDP 3478-3479 (PSN Voice Chat)
- TCP 3658 (PSN)

### Fail2ban Configuration
Fail2ban monitors logs and blocks suspicious IP addresses automatically.

1. Copy fail2ban configurations to /etc/fail2ban/
2. Enable and start:
   sudo systemctl enable --now fail2ban
   sudo systemctl status fail2ban
3. Check banned IPs:
   sudo fail2ban-client status

### PS5 Network Optimization
For optimal PS5 performance:
1. Set PS5 to use static IP in your router
2. Configure PS5 DNS to use RPi IP (Unbound)
3. Configure PS5 proxy to use RPi IP:3128 (Squid)
4. Enable DMZ or port forwarding for PS5 IP in router (optional)
5. Set PS5 MTU to 1473 for PPPoE or 1500 for standard connections

