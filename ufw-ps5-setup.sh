#!/usr/bin/env bash
# UFW Firewall Setup Script for Raspberry Pi 3B+ with PS5 Optimization
# This script configures UFW with rules optimized for PS5 gaming and network services

set -euo pipefail

echo "=== UFW Firewall Setup for RPi 3B+ with PS5 ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root or with sudo"
    exit 1
fi

# Reset UFW to default state (optional - comment out if you want to keep existing rules)
echo "Resetting UFW to default..."
ufw --force reset

# Set default policies
echo "Setting default policies..."
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (change port if you use non-standard)
echo "Allowing SSH..."
ufw allow 22/tcp comment 'SSH'

# Allow web dashboard
echo "Allowing web dashboard (port 8080)..."
ufw allow 8080/tcp comment 'Python Firewall Dashboard'

# Allow HTTP/HTTPS (for Squid proxy and general web access)
echo "Allowing HTTP/HTTPS..."
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# Allow Squid proxy
echo "Allowing Squid proxy..."
ufw allow 3128/tcp comment 'Squid Proxy'

# Allow DNS (Unbound)
echo "Allowing DNS queries..."
ufw allow 53/tcp comment 'DNS TCP'
ufw allow 53/udp comment 'DNS UDP'

# PS5 Network Ports
echo "Configuring PS5-specific ports..."

# PSN connectivity (HTTP/HTTPS already allowed above)
ufw allow 3478:3480/tcp comment 'PS5 PSN'
ufw allow 3478:3479/udp comment 'PS5 Voice Chat'

# Additional PS5 ports
ufw allow 3658/tcp comment 'PS5 PSN Additional'
ufw allow 3659/tcp comment 'PS5 PSN Additional'
ufw allow 10070:10080/tcp comment 'PS5 Game Servers'
ufw allow 10070:10080/udp comment 'PS5 Game Servers'

# PS5 Remote Play (if needed)
# ufw allow 9295:9304/tcp comment 'PS5 Remote Play'
# ufw allow 9296:9297/udp comment 'PS5 Remote Play'

# Allow mDNS/Bonjour (for local network discovery)
echo "Allowing local network discovery..."
ufw allow 5353/udp comment 'mDNS'

# Allow DHCP client
echo "Allowing DHCP..."
ufw allow 67:68/udp comment 'DHCP'

# Allow local network completely (adjust subnet as needed)
# Uncomment if you trust your local network completely
# echo "Allowing all local network traffic..."
# ufw allow from 192.168.0.0/16 comment 'Local Network'

# Enable UFW
echo "Enabling UFW..."
ufw --force enable

# Show status
echo ""
echo "=== UFW Configuration Complete ==="
echo ""
ufw status verbose

echo ""
echo "=== Setup Complete ==="
echo "UFW is now configured and enabled with PS5-optimized rules."
echo ""
echo "Important notes:"
echo "1. Make sure your PS5 is configured to use this RPi as proxy (IP:3128)"
echo "2. Configure PS5 DNS to use this RPi's IP address"
echo "3. Consider setting static IP for PS5 in your router"
echo "4. For PS5 Remote Play, uncomment the remote play rules in this script"
echo ""
echo "To check firewall status: sudo ufw status verbose"
echo "To disable firewall: sudo ufw disable"
echo "To see numbered rules: sudo ufw status numbered"
echo "To delete a rule: sudo ufw delete [number]"
