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
USE_NFT = os.environ.get("USE_NFT", "true").lower() in ("1", "true", "yes")  # if false, will try iptables

# Basic HTML template (tiny)
TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>pythonfirewall - {{host}}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    pre { background:#f4f4f4; padding:10px; overflow:auto; max-height:60vh; }
    .warn { color: #8b0000; font-weight: bold; }
    .ok { color: #006400; }
  </style>
</head>
<body>
  <h1>pythonfirewall</h1>
  <p>Host: <strong>{{host}}</strong></p>
  <p>Firewall control: <strong class="{{'ok' if allow else 'warn'}}">{{'ENABLED' if allow else 'DISABLED'}}</strong></p>
  <ul>
    <li><a href="{{url_for('rules')}}">View firewall rules</a> (requires admin)</li>
    {% if allow %}
    <li><a href="{{url_for('apply_page')}}">Apply a sample rule</a> (dangerous, requires sudo config)</li>
    {% endif %}
    <li><a href="{{url_for('about')}}">About</a></li>
  </ul>
</body>
</html>
"""

ABOUT = """
<!doctype html>
<html><body>
<h2>About pythonfirewall</h2>
<p>Simple control panel. This server is intended for local network use only unless you explicitly configure secure access (SSH keys, firewall, HTTPS, reverse proxy).</p>
<p>Do NOT enable remote (internet-facing) control without additional protections (TLS, VPN, or trusted reverse tunnel).</p>
</body></html>
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
    if USE_NFT:
        cmd = ["/usr/sbin/nft", "list", "ruleset"]
    else:
        cmd = ["/sbin/iptables", "-S"]
    code, out = run_cmd(cmd)
    if code != 0:
        content = f"Error running {' '.join(cmd)} (code {code}):\n\n{out}"
    else:
        content = out
    html = "<h2>Firewall rules</h2><pre>{}</pre><p><a href='/'>Back</a></p>".format(
        content.replace("<", "&lt;")
    )
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
            sample = "sudo iptables -A INPUT -p tcp --dport 2222 -j ACCEPT"
        return render_template_string(
            """
            <h2>Apply a firewall command (DANGEROUS)</h2>
            <p class="warn">This will run the submitted command as root (via sudo). Only enable after configuring sudoers for the web user.</p>
            <form method="post">
              <label>Command to run (exact):</label><br/>
              <input name="cmd" style="width:90%" value="{{sample}}"/><br/><br/>
              <input type="submit" value="Run"/>
            </form>
            <p><a href='/'>Back</a></p>
            """,
            sample=sample,
        )
    cmd_text = request.form.get("cmd", "")
    if not cmd_text:
        return "No command provided", 400
    cmd_list = shlex.split(cmd_text)
    code, out = run_cmd(["sudo"] + cmd_list, timeout=15)
    return "<h2>Command result</h2><pre>{}</pre><p><a href='/'>Back</a></p>".format(
        f"Exit {code}\n{out}".replace("<", "&lt;")
    )


if __name__ == "__main__":
    print(f"Starting pythonfirewall on 0.0.0.0:{PORT}, NFT enabled: {USE_NFT}, firewall control: {ALLOW_FIREWALL_CONTROL}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
