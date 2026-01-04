#!/usr/bin/env python3
"""
Simple Flask-based web dashboard for "pythonfirewall" on Raspberry Pi (Kali).
- Binds to 0.0.0.0 so devices on the same LAN can access it.
- Basic HTTP auth using environment variables (ADMIN_USER, ADMIN_PASS).
- Endpoint /rules runs 'nft list ruleset' (or iptables -S) and shows output.
- Endpoint /apply exists but is disabled by default; enable only after
  configuring secure sudoers and understanding risks.
"""

import os
import subprocess
import shlex
from functools import wraps
from base64 import b64decode
from flask import Flask, request, Response, render_template_string, abort

app = Flask(__name__)

# Configuration via environment variables:
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "changeme")  # change before exposing!
PORT = int(os.environ.get("PORT", "8080"))
ALLOW_FIREWALL_CONTROL = os.environ.get("ALLOW_FIREWALL_CONTROL", "false").lower() in ("1", "true", "yes")
USE_NFT = os.environ.get("USE_NFT", "false").lower() in ("1", "true", "yes")  # if false, will try UFW/iptables

# Basic HTML template (tiny)
TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>pythonfirewall - {{host}}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
    .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
    h2 { color: #555; margin-top: 20px; }
    pre { background:#f4f4f4; padding:10px; overflow:auto; max-height:60vh; border-radius: 4px; border: 1px solid #ddd; }
    .warn { color: #8b0000; font-weight: bold; }
    .ok { color: #006400; }
    .info { color: #0066cc; }
    ul { list-style: none; padding: 0; }
    li { margin: 10px 0; }
    a { color: #0066cc; text-decoration: none; padding: 8px 12px; background: #e8f4f8; border-radius: 4px; display: inline-block; }
    a:hover { background: #d0e8f0; }
    .status-box { background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 4px; border-left: 4px solid #4CAF50; }
    .service-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin: 20px 0; }
    .service-card { background: #fff; border: 1px solid #ddd; border-radius: 4px; padding: 15px; }
    .service-name { font-weight: bold; color: #333; margin-bottom: 5px; }
    .service-status { font-size: 0.9em; color: #666; }
  </style>
</head>
<body>
  <div class="container">
    <h1>🔥 pythonfirewall - RPi 3B+ with PS5</h1>
    <div class="status-box">
      <p>Host: <strong>{{host}}</strong></p>
      <p>Firewall control: <strong class="{{'ok' if allow else 'warn'}}">{{'ENABLED' if allow else 'DISABLED'}}</strong></p>
      <p>Platform: <strong class="info">Raspberry Pi 3B+ with Squid, Unbound, UFW, Fail2ban</strong></p>
    </div>
    
    <h2>📋 Quick Links</h2>
    <ul>
      <li><a href="{{url_for('rules')}}">🛡️ View firewall rules (UFW/NFT)</a></li>
      <li><a href="{{url_for('services_status')}}">📊 Service status (Squid, Unbound, Fail2ban)</a></li>
      <li><a href="{{url_for('ps5_info')}}">🎮 PS5 Configuration Guide</a></li>
      {% if allow %}
      <li><a href="{{url_for('apply_page')}}">⚙️ Apply firewall rule (requires sudo)</a></li>
      {% endif %}
      <li><a href="{{url_for('about')}}">ℹ️ About</a></li>
    </ul>
  </div>
</body>
</html>
"""

ABOUT = """
<!doctype html>
<html>
<head>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
    .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
    h2 { color: #333; }
    p { line-height: 1.6; color: #666; }
    .highlight { background: #fff3cd; padding: 10px; border-radius: 4px; margin: 10px 0; }
  </style>
</head>
<body>
  <div class="container">
    <h2>About pythonfirewall</h2>
    <p>Advanced firewall control panel for Raspberry Pi 3B+ with PS5 gaming optimization.</p>
    
    <h3>Integrated Components:</h3>
    <ul>
      <li><strong>Squid Proxy:</strong> HTTP/HTTPS caching for faster game downloads</li>
      <li><strong>Unbound DNS:</strong> Fast, secure DNS resolution with DNSSEC</li>
      <li><strong>UFW Firewall:</strong> Simplified firewall with PS5-optimized rules</li>
      <li><strong>Fail2ban:</strong> Automated intrusion prevention</li>
    </ul>
    
    <div class="highlight">
      <strong>⚠️ Security Notice:</strong>
      <p>This server is intended for local network use only. Do NOT enable remote (internet-facing) control without additional protections (TLS, VPN, or trusted reverse tunnel).</p>
    </div>
    
    <p><a href="/">← Back to Dashboard</a></p>
  </div>
</body>
</html>
"""


def check_auth_header():
    auth = request.headers.get("Authorization")
    if not auth:
        return False
    try:
        method, encoded = auth.split(None, 1)
        if method.lower() != "basic":
            return False
        decoded = b64decode(encoded).decode("utf-8")
        user, passwd = decoded.split(":", 1)
        return user == ADMIN_USER and passwd == ADMIN_PASS
    except Exception:
        return False


def require_basic_auth(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not check_auth_header():
            return Response("Unauthorized", 401, {"WWW-Authenticate": 'Basic realm="Login Required"'})
        return f(*args, **kwargs)
    return decorated


def run_cmd(cmd_list, timeout=8):
    """Run command and return (exitcode, stdout). cmd_list is list."""
    try:
        out = subprocess.check_output(cmd_list, stderr=subprocess.STDOUT, timeout=timeout)
        return 0, out.decode("utf-8", errors="replace")
    except subprocess.CalledProcessError as e:
        return e.returncode, e.output.decode("utf-8", errors="replace")
    except Exception as e:
        return 255, str(e)


@app.route("/")
@require_basic_auth
def index():
    host = request.host
    return render_template_string(TEMPLATE, host=host, allow=ALLOW_FIREWALL_CONTROL)


@app.route("/about")
@require_basic_auth
def about():
    return ABOUT


@app.route("/rules")
@require_basic_auth
def rules():
    # Try UFW first (preferred for this setup), then NFT, then iptables
    if USE_NFT:
        cmd = ["/usr/sbin/nft", "list", "ruleset"]
        label = "NFT"
    else:
        # Try UFW first
        cmd = ["sudo", "/usr/sbin/ufw", "status", "verbose"]
        label = "UFW"
    
    code, out = run_cmd(cmd)
    
    # If UFW not available, try iptables
    if code != 0 and not USE_NFT:
        cmd = ["/sbin/iptables", "-S"]
        label = "iptables"
        code, out = run_cmd(cmd)
    
    if code != 0:
        content = f"Error running {' '.join(cmd)} (code {code}):\n\n{out}"
    else:
        content = out
    
    html = f"""
    <html>
    <head>
      <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        h2 {{ color: #333; }}
        pre {{ background:#f4f4f4; padding:15px; overflow:auto; max-height:70vh; border-radius: 4px; border: 1px solid #ddd; }}
        a {{ color: #0066cc; text-decoration: none; padding: 8px 12px; background: #e8f4f8; border-radius: 4px; display: inline-block; }}
      </style>
    </head>
    <body>
      <div class="container">
        <h2>🛡️ Firewall Rules ({label})</h2>
        <pre>{content.replace("<", "&lt;")}</pre>
        <p><a href='/'>← Back to Dashboard</a></p>
      </div>
    </body>
    </html>
    """
    return html


@app.route("/apply", methods=["GET", "POST"])
@require_basic_auth
def apply_page():
    if not ALLOW_FIREWALL_CONTROL:
        abort(403, "Firewall control is disabled on this server.")
    if request.method == "GET":
        sample = ""
        if USE_NFT:
            sample = "sudo nft add rule inet filter input tcp dport 2222 accept"
        else:
            sample = "sudo ufw allow 2222/tcp comment 'Custom Rule'"
        return render_template_string(
            """
            <html>
            <head>
              <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
                .warn { color: #8b0000; font-weight: bold; background: #fff3cd; padding: 10px; border-radius: 4px; }
                input[type="text"] { width: 90%; padding: 8px; font-family: monospace; }
                input[type="submit"] { padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; }
              </style>
            </head>
            <body>
              <div class="container">
                <h2>⚙️ Apply Firewall Command</h2>
                <p class="warn">⚠️ This will run the submitted command as root (via sudo). Only enable after configuring sudoers for the web user.</p>
                <form method="post">
                  <label>Command to run (exact):</label><br/>
                  <input name="cmd" type="text" value="{{sample}}"/><br/><br/>
                  <input type="submit" value="Run Command"/>
                </form>
                <p><a href='/'>← Back to Dashboard</a></p>
              </div>
            </body>
            </html>
            """,
            sample=sample,
        )
    cmd_text = request.form.get("cmd", "")
    if not cmd_text:
        return "No command provided", 400
    cmd_list = shlex.split(cmd_text)
    code, out = run_cmd(["sudo"] + cmd_list, timeout=15)
    return f"""
    <html>
    <head>
      <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        pre {{ background:#f4f4f4; padding:15px; overflow:auto; border-radius: 4px; border: 1px solid #ddd; }}
      </style>
    </head>
    <body>
      <div class="container">
        <h2>Command Result</h2>
        <pre>{f"Exit {code}\n{out}".replace("<", "&lt;")}</pre>
        <p><a href='/'>← Back to Dashboard</a></p>
      </div>
    </body>
    </html>
    """


@app.route("/services")
@require_basic_auth
def services_status():
    """Display status of all integrated services: Squid, Unbound, UFW, Fail2ban"""
    services = ["squid", "unbound", "fail2ban"]
    status_info = {}
    
    for service in services:
        cmd = ["systemctl", "is-active", service]
        code, out = run_cmd(cmd)
        status_info[service] = {
            "active": code == 0 and "active" in out.lower(),
            "status": out.strip()
        }
    
    # Get UFW status
    ufw_code, ufw_out = run_cmd(["sudo", "/usr/sbin/ufw", "status"])
    ufw_active = "Status: active" in ufw_out
    
    # Get Fail2ban banned IPs
    f2b_code, f2b_out = run_cmd(["sudo", "fail2ban-client", "status"])
    
    html = f"""
    <html>
    <head>
      <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        h2 {{ color: #333; }}
        .service-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin: 20px 0; }}
        .service-card {{ background: #fff; border: 1px solid #ddd; border-radius: 4px; padding: 15px; }}
        .service-card.active {{ border-left: 4px solid #4CAF50; }}
        .service-card.inactive {{ border-left: 4px solid #dc3545; }}
        .service-name {{ font-weight: bold; font-size: 1.2em; margin-bottom: 10px; }}
        .status-badge {{ padding: 4px 8px; border-radius: 4px; font-size: 0.9em; display: inline-block; }}
        .status-active {{ background: #d4edda; color: #155724; }}
        .status-inactive {{ background: #f8d7da; color: #721c24; }}
        pre {{ background:#f4f4f4; padding:15px; overflow:auto; max-height:300px; border-radius: 4px; border: 1px solid #ddd; font-size: 0.85em; }}
        a {{ color: #0066cc; text-decoration: none; padding: 8px 12px; background: #e8f4f8; border-radius: 4px; display: inline-block; }}
      </style>
    </head>
    <body>
      <div class="container">
        <h2>📊 Service Status</h2>
        
        <div class="service-grid">
          <div class="service-card {'active' if status_info['squid']['active'] else 'inactive'}">
            <div class="service-name">Squid Proxy</div>
            <span class="status-badge {'status-active' if status_info['squid']['active'] else 'status-inactive'}">
              {status_info['squid']['status']}
            </span>
            <p style="margin-top:10px; font-size:0.9em; color:#666;">HTTP/HTTPS caching proxy for faster downloads</p>
          </div>
          
          <div class="service-card {'active' if status_info['unbound']['active'] else 'inactive'}">
            <div class="service-name">Unbound DNS</div>
            <span class="status-badge {'status-active' if status_info['unbound']['active'] else 'status-inactive'}">
              {status_info['unbound']['status']}
            </span>
            <p style="margin-top:10px; font-size:0.9em; color:#666;">Secure DNS resolver with DNSSEC</p>
          </div>
          
          <div class="service-card {'active' if ufw_active else 'inactive'}">
            <div class="service-name">UFW Firewall</div>
            <span class="status-badge {'status-active' if ufw_active else 'status-inactive'}">
              {'Active' if ufw_active else 'Inactive'}
            </span>
            <p style="margin-top:10px; font-size:0.9em; color:#666;">PS5-optimized firewall rules</p>
          </div>
          
          <div class="service-card {'active' if status_info['fail2ban']['active'] else 'inactive'}">
            <div class="service-name">Fail2ban</div>
            <span class="status-badge {'status-active' if status_info['fail2ban']['active'] else 'status-inactive'}">
              {status_info['fail2ban']['status']}
            </span>
            <p style="margin-top:10px; font-size:0.9em; color:#666;">Intrusion prevention system</p>
          </div>
        </div>
        
        <h3>UFW Status Details</h3>
        <pre>{ufw_out.replace("<", "&lt;")}</pre>
        
        <h3>Fail2ban Status</h3>
        <pre>{f2b_out.replace("<", "&lt;")}</pre>
        
        <p><a href='/'>← Back to Dashboard</a></p>
      </div>
    </body>
    </html>
    """
    return html


@app.route("/ps5")
@require_basic_auth
def ps5_info():
    """Display PS5 configuration guide"""
    # Try to get the server's IP address
    try:
        hostname_cmd = ["hostname", "-I"]
        code, ip_out = run_cmd(hostname_cmd)
        server_ip = ip_out.strip().split()[0] if code == 0 else "YOUR_RPI_IP"
    except:
        server_ip = "YOUR_RPI_IP"
    
    html = f"""
    <html>
    <head>
      <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        h2 {{ color: #333; border-bottom: 3px solid #0070cc; padding-bottom: 10px; }}
        h3 {{ color: #555; margin-top: 25px; }}
        .step {{ background: #f9f9f9; padding: 15px; margin: 15px 0; border-radius: 4px; border-left: 4px solid #0070cc; }}
        .step-number {{ background: #0070cc; color: white; padding: 5px 10px; border-radius: 50%; font-weight: bold; margin-right: 10px; }}
        .highlight {{ background: #fff3cd; padding: 10px; border-radius: 4px; margin: 10px 0; border-left: 4px solid #ffc107; }}
        .info-box {{ background: #e7f3ff; padding: 15px; border-radius: 4px; margin: 15px 0; border-left: 4px solid #0070cc; }}
        code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: monospace; }}
        ul {{ line-height: 1.8; }}
        a {{ color: #0066cc; text-decoration: none; padding: 8px 12px; background: #e8f4f8; border-radius: 4px; display: inline-block; }}
      </style>
    </head>
    <body>
      <div class="container">
        <h2>🎮 PS5 Network Configuration Guide</h2>
        
        <div class="info-box">
          <strong>📡 Your Raspberry Pi IP Address:</strong> <code>{server_ip}</code><br>
          Use this IP address in the configuration steps below.
        </div>
        
        <h3>Quick Setup Steps</h3>
        
        <div class="step">
          <span class="step-number">1</span>
          <strong>Configure DNS on PS5</strong>
          <ul>
            <li>Go to: Settings → Network → Settings → Set Up Internet Connection</li>
            <li>Select your network (WiFi or LAN)</li>
            <li>Choose "Advanced Settings"</li>
            <li>DNS Settings → Manual</li>
            <li>Primary DNS: <code>{server_ip}</code></li>
            <li>Secondary DNS: <code>1.1.1.1</code> (Cloudflare backup)</li>
          </ul>
        </div>
        
        <div class="step">
          <span class="step-number">2</span>
          <strong>Configure Proxy on PS5</strong>
          <ul>
            <li>Continue in Advanced Settings</li>
            <li>Proxy Server → Use</li>
            <li>Address: <code>{server_ip}</code></li>
            <li>Port: <code>3128</code></li>
          </ul>
        </div>
        
        <div class="step">
          <span class="step-number">3</span>
          <strong>Set Static IP for PS5 (Recommended)</strong>
          <ul>
            <li>Go to your router's admin panel</li>
            <li>Find DHCP settings or Connected Devices</li>
            <li>Assign a static/reserved IP to your PS5's MAC address</li>
            <li>This ensures consistent connectivity</li>
          </ul>
        </div>
        
        <div class="step">
          <span class="step-number">4</span>
          <strong>Test Connection</strong>
          <ul>
            <li>On PS5: Settings → Network → Test Internet Connection</li>
            <li>Verify all tests pass</li>
            <li>Check NAT Type (Type 2 or Type 1 is ideal)</li>
          </ul>
        </div>
        
        <h3>🚀 Performance Tips</h3>
        <ul>
          <li><strong>MTU Setting:</strong> Try 1473 if you have connection issues (PPPoE), otherwise 1500</li>
          <li><strong>Wired Connection:</strong> Use Ethernet cable for best performance</li>
          <li><strong>Router QoS:</strong> Enable Quality of Service and prioritize PS5 traffic</li>
          <li><strong>Port Forwarding:</strong> Consider DMZ or port forwarding for best NAT type</li>
        </ul>
        
        <h3>🔍 Troubleshooting</h3>
        <div class="highlight">
          <strong>If connection fails:</strong>
          <ul>
            <li>Verify Raspberry Pi services are running (check <a href="/services">Service Status</a>)</li>
            <li>Ensure firewall rules allow PS5 traffic: <code>sudo ufw status</code></li>
            <li>Check Squid logs: <code>sudo tail -f /var/log/squid/access.log</code></li>
            <li>Verify Unbound is resolving DNS: <code>dig google.com @{server_ip}</code></li>
          </ul>
        </div>
        
        <h3>📋 PS5 Required Ports (Already Configured)</h3>
        <ul>
          <li>TCP 80, 443 - HTTP/HTTPS</li>
          <li>TCP 3478-3480 - PSN Services</li>
          <li>UDP 3478-3479 - Voice Chat</li>
          <li>TCP 3658, 3659 - PSN Additional</li>
          <li>TCP/UDP 10070-10080 - Game Servers</li>
        </ul>
        
        <div class="info-box">
          <strong>💡 Pro Tip:</strong> For the best gaming experience, connect your PS5 via Ethernet cable 
          and ensure your Raspberry Pi also has a wired connection to your router.
        </div>
        
        <p style="margin-top: 30px;"><a href='/'>← Back to Dashboard</a></p>
      </div>
    </body>
    </html>
    """
    return html


if __name__ == "__main__":
    print(f"Starting pythonfirewall on 0.0.0.0:{PORT}")
    print(f"Platform: Raspberry Pi 3B+ with Squid, Unbound, UFW, Fail2ban")
    print(f"NFT enabled: {USE_NFT}, Firewall control: {ALLOW_FIREWALL_CONTROL}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
