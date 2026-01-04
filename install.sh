#!/usr/bin/env bash
# Complete installation script for Raspberry Pi 3B+ Firewall with PS5 support
# Installs and configures: Squid, Unbound, UFW, Fail2ban, and Python Firewall Dashboard

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Raspberry Pi 3B+ Firewall Installation ===${NC}"
echo "This script will install and configure:"
echo "  - Squid Proxy (for caching and PS5 optimization)"
echo "  - Unbound DNS (for local DNS resolution)"
echo "  - UFW Firewall (with PS5-specific rules)"
echo "  - Fail2ban (for intrusion prevention)"
echo "  - Python Firewall Dashboard"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Script directory: $SCRIPT_DIR"
echo ""

# Update system
echo -e "${YELLOW}[1/8] Updating system packages...${NC}"
apt update
apt upgrade -y

# Install required packages
echo -e "${YELLOW}[2/8] Installing required packages...${NC}"
apt install -y python3 python3-venv python3-pip git nginx squid unbound ufw fail2ban

# Configure Squid
echo -e "${YELLOW}[3/8] Configuring Squid proxy...${NC}"
if [ -f "$SCRIPT_DIR/squid.conf" ]; then
    cp /etc/squid/squid.conf /etc/squid/squid.conf.backup.$(date +%Y%m%d)
    cp "$SCRIPT_DIR/squid.conf" /etc/squid/squid.conf
    
    # Create cache directory and set permissions
    mkdir -p /var/spool/squid
    chown -R proxy:proxy /var/spool/squid
    
    # Initialize cache
    squid -z
    
    # Enable and start Squid
    systemctl enable squid
    systemctl restart squid
    echo -e "${GREEN}Squid configured and started${NC}"
else
    echo -e "${RED}Warning: squid.conf not found, skipping Squid configuration${NC}"
fi

# Configure Unbound
echo -e "${YELLOW}[4/8] Configuring Unbound DNS...${NC}"
if [ -f "$SCRIPT_DIR/unbound.conf" ]; then
    mkdir -p /etc/unbound/unbound.conf.d
    cp "$SCRIPT_DIR/unbound.conf" /etc/unbound/unbound.conf.d/custom.conf
    
    # Create log directory
    mkdir -p /var/log/unbound
    chown unbound:unbound /var/log/unbound
    
    # Download root hints
    wget -O /var/lib/unbound/root.hints https://www.internic.net/domain/named.cache || true
    
    # Create root key if it doesn't exist
    if [ ! -f /var/lib/unbound/root.key ]; then
        unbound-anchor -a /var/lib/unbound/root.key || true
    fi
    
    # Set ownership
    chown -R unbound:unbound /var/lib/unbound
    
    # Enable and start Unbound
    systemctl enable unbound
    systemctl restart unbound
    echo -e "${GREEN}Unbound configured and started${NC}"
else
    echo -e "${RED}Warning: unbound.conf not found, skipping Unbound configuration${NC}"
fi

# Configure UFW
echo -e "${YELLOW}[5/8] Configuring UFW firewall...${NC}"
if [ -f "$SCRIPT_DIR/ufw-ps5-setup.sh" ]; then
    chmod +x "$SCRIPT_DIR/ufw-ps5-setup.sh"
    bash "$SCRIPT_DIR/ufw-ps5-setup.sh"
    echo -e "${GREEN}UFW configured${NC}"
else
    echo -e "${RED}Warning: ufw-ps5-setup.sh not found, skipping UFW configuration${NC}"
fi

# Configure Fail2ban
echo -e "${YELLOW}[6/8] Configuring Fail2ban...${NC}"
if [ -f "$SCRIPT_DIR/fail2ban-jail.local" ]; then
    cp "$SCRIPT_DIR/fail2ban-jail.local" /etc/fail2ban/jail.local
    
    # Copy custom filters
    if [ -f "$SCRIPT_DIR/fail2ban-squid-filter.conf" ]; then
        cp "$SCRIPT_DIR/fail2ban-squid-filter.conf" /etc/fail2ban/filter.d/squid.conf
    fi
    
    # Enable and start Fail2ban
    systemctl enable fail2ban
    systemctl restart fail2ban
    echo -e "${GREEN}Fail2ban configured and started${NC}"
else
    echo -e "${RED}Warning: fail2ban configuration not found, skipping Fail2ban configuration${NC}"
fi

# Setup Python Firewall Dashboard
echo -e "${YELLOW}[7/8] Setting up Python Firewall Dashboard...${NC}"

# Create user for the service
if ! id "pyfw" &>/dev/null; then
    adduser --disabled-login --gecos "PythonFirewall" pyfw
    echo -e "${GREEN}Created pyfw user${NC}"
fi

# Setup Python environment
INSTALL_DIR="/home/pyfw/pythonfirewall"
mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR"/*.py "$INSTALL_DIR/" || true
cp "$SCRIPT_DIR"/*.txt "$INSTALL_DIR/" || true
cp "$SCRIPT_DIR"/*.service "$INSTALL_DIR/" || true

# Create virtual environment and install dependencies
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi
deactivate

# Set ownership
chown -R pyfw:pyfw "$INSTALL_DIR"

# Create environment file
echo -e "${YELLOW}Creating environment configuration...${NC}"
cat > /etc/default/pythonfirewall <<EOF
ADMIN_USER="admin"
ADMIN_PASS="$(openssl rand -base64 24)"
PORT="8080"
ALLOW_FIREWALL_CONTROL="false"
USE_NFT="false"
EOF

echo -e "${GREEN}Environment file created at /etc/default/pythonfirewall${NC}"
echo -e "${RED}IMPORTANT: Edit /etc/default/pythonfirewall and change ADMIN_PASS!${NC}"

# Install systemd service
if [ -f "$INSTALL_DIR/pythonfirewall.service" ]; then
    cp "$INSTALL_DIR/pythonfirewall.service" /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable pythonfirewall
    systemctl start pythonfirewall
    echo -e "${GREEN}Python Firewall Dashboard service installed and started${NC}"
fi

# Configure sudoers for firewall control (optional)
echo -e "${YELLOW}[8/8] Configuring sudoers (optional)...${NC}"
if ! grep -q "pyfw ALL=(root) NOPASSWD: /usr/sbin/ufw" /etc/sudoers 2>/dev/null; then
    echo "pyfw ALL=(root) NOPASSWD: /usr/sbin/ufw" >> /etc/sudoers.d/pyfw
    chmod 0440 /etc/sudoers.d/pyfw
    echo -e "${GREEN}Sudoers configured for UFW access${NC}"
fi

# Final status check
echo ""
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo ""
echo "Service Status:"
echo "---------------"
systemctl status squid --no-pager | head -3
systemctl status unbound --no-pager | head -3
systemctl status fail2ban --no-pager | head -3
systemctl status pythonfirewall --no-pager | head -3
echo ""
echo "UFW Status:"
ufw status verbose
echo ""
echo -e "${GREEN}=== Next Steps ===${NC}"
echo "1. Edit /etc/default/pythonfirewall and change ADMIN_PASS"
echo "2. Restart dashboard: sudo systemctl restart pythonfirewall"
echo "3. Access dashboard at: http://$(hostname -I | awk '{print $1}'):8080"
echo "4. Configure PS5:"
echo "   - Set DNS to: $(hostname -I | awk '{print $1}')"
echo "   - Set Proxy to: $(hostname -I | awk '{print $1}'):3128"
echo "5. Consider setting static IP for your Raspberry Pi"
echo ""
echo -e "${YELLOW}Default credentials: admin / (see /etc/default/pythonfirewall)${NC}"
echo ""
