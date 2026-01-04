# Quick Start Guide - Raspberry Pi 3B+ Firewall with PS5

## Overview
This firewall solution provides a comprehensive network security and optimization setup for your Raspberry Pi 3B+, specifically optimized for PlayStation 5 gaming.

## Components
- **Squid Proxy**: HTTP/HTTPS caching for faster game downloads
- **Unbound DNS**: Secure, fast DNS resolution with DNSSEC
- **UFW Firewall**: Simplified firewall with PS5-optimized rules
- **Fail2ban**: Automated intrusion prevention
- **Python Dashboard**: Web-based management interface

## Installation

### One-Line Installation
```bash
sudo bash install.sh
```

This will:
1. Update system packages
2. Install all required components
3. Configure services with optimal settings
4. Set up the web dashboard
5. Enable and start all services

### Manual Installation

If you prefer step-by-step installation:

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install packages
sudo apt install -y python3 python3-venv python3-pip git nginx squid unbound ufw fail2ban

# 3. Configure Squid
sudo cp squid.conf /etc/squid/squid.conf
sudo squid -z
sudo systemctl enable --now squid

# 4. Configure Unbound
sudo mkdir -p /etc/unbound/unbound.conf.d
sudo cp unbound.conf /etc/unbound/unbound.conf.d/custom.conf
sudo systemctl enable --now unbound

# 5. Configure UFW
sudo chmod +x ufw-ps5-setup.sh
sudo ./ufw-ps5-setup.sh

# 6. Configure Fail2ban
sudo cp fail2ban-jail.local /etc/fail2ban/jail.local
sudo cp fail2ban-squid-filter.conf /etc/fail2ban/filter.d/squid.conf
sudo systemctl enable --now fail2ban

# 7. Setup Python Dashboard
sudo adduser --disabled-login --gecos "PythonFirewall" pyfw
sudo -u pyfw python3 -m venv /home/pyfw/pythonfirewall/venv
sudo -u pyfw /home/pyfw/pythonfirewall/venv/bin/pip install -r requirements.txt
sudo cp pythonfirewall.service /etc/systemd/system/
sudo systemctl enable --now pythonfirewall
```

## Configuration

### 1. Change Default Password
```bash
sudo nano /etc/default/pythonfirewall
# Change ADMIN_PASS to a strong password
sudo systemctl restart pythonfirewall
```

### 2. Get Your Raspberry Pi IP Address
```bash
hostname -I
```
Note this IP address - you'll need it for PS5 configuration.

### 3. Configure Your PS5

#### DNS Settings
1. PS5: Settings → Network → Settings → Set Up Internet Connection
2. Select your network → Advanced Settings
3. DNS Settings → Manual
4. Primary DNS: `[Your RPi IP]`
5. Secondary DNS: `1.1.1.1`

#### Proxy Settings
1. Continue in Advanced Settings
2. Proxy Server → Use
3. Address: `[Your RPi IP]`
4. Port: `3128`

#### Test Connection
1. PS5: Settings → Network → Test Internet Connection
2. Verify all tests pass

## Accessing the Dashboard

Open a web browser on any device on your network:
```
http://[Your RPi IP]:8080
```

Default credentials:
- Username: `admin`
- Password: Check `/etc/default/pythonfirewall`

## Service Management

### Check Service Status
```bash
# All services
sudo systemctl status squid unbound fail2ban pythonfirewall

# Individual services
sudo systemctl status squid
sudo systemctl status unbound
sudo systemctl status fail2ban
sudo systemctl status pythonfirewall
```

### View Logs
```bash
# Squid logs
sudo tail -f /var/log/squid/access.log

# Unbound logs
sudo tail -f /var/log/unbound/unbound.log

# Fail2ban status
sudo fail2ban-client status

# UFW status
sudo ufw status verbose
```

### Restart Services
```bash
sudo systemctl restart squid
sudo systemctl restart unbound
sudo systemctl restart fail2ban
sudo systemctl restart pythonfirewall
```

## Performance Optimization

### For Raspberry Pi 3B+
1. Use a quality SD card (Class 10 or better, UHS-1 recommended)
2. Ensure adequate cooling (heatsinks or fan)
3. Use Ethernet connection for best performance
4. Adjust Squid cache size based on available storage

### For PS5
1. Use wired (Ethernet) connection
2. Set static IP for PS5 in router
3. Enable router QoS and prioritize PS5
4. Consider DMZ or port forwarding for NAT Type 1

## Troubleshooting

### PS5 Can't Connect
```bash
# Check all services are running
sudo systemctl status squid unbound fail2ban

# Check firewall rules
sudo ufw status verbose

# Test DNS resolution
dig google.com @127.0.0.1

# Check Squid
sudo tail -f /var/log/squid/access.log
```

### Dashboard Not Accessible
```bash
# Check service status
sudo systemctl status pythonfirewall

# Check logs
sudo journalctl -u pythonfirewall -f

# Verify port is listening
sudo netstat -tlnp | grep 8080
```

### Slow Downloads on PS5
1. Verify Squid cache is working: `sudo du -sh /var/spool/squid`
2. Check available disk space: `df -h`
3. Monitor network: `sudo iftop` or `sudo nethogs`
4. Review Squid cache log: `sudo tail -f /var/log/squid/cache.log`

## Security Considerations

1. **Change default password** immediately after installation
2. **Firewall**: UFW is configured to block unauthorized access
3. **Fail2ban**: Automatically blocks repeated failed login attempts
4. **Network**: Only expose dashboard to trusted local network
5. **Updates**: Regularly update system: `sudo apt update && sudo apt upgrade`

## Advanced Configuration

### Adjust Squid Cache Size
Edit `/etc/squid/squid.conf`:
```bash
sudo nano /etc/squid/squid.conf
# Find: cache_dir ufs /var/spool/squid 10000 16 256
# Change 10000 (MB) to desired size
sudo systemctl restart squid
```

### Add Custom UFW Rules
```bash
# Allow specific port
sudo ufw allow 8888/tcp comment 'Custom Service'

# Allow from specific IP
sudo ufw allow from 192.168.1.100 comment 'Trusted Device'

# Delete rule by number
sudo ufw status numbered
sudo ufw delete [number]
```

### Configure Fail2ban Ban Time
Edit `/etc/fail2ban/jail.local`:
```bash
sudo nano /etc/fail2ban/jail.local
# Change bantime, findtime, maxretry as needed
sudo systemctl restart fail2ban
```

## Maintenance

### Regular Tasks
```bash
# Update system (monthly)
sudo apt update && sudo apt upgrade -y

# Check disk space
df -h

# Review blocked IPs
sudo fail2ban-client status

# Clear old logs (if needed)
sudo journalctl --vacuum-time=30d
```

### Backup Configuration
```bash
# Backup important configs
sudo tar -czf firewall-backup-$(date +%Y%m%d).tar.gz \
  /etc/squid/squid.conf \
  /etc/unbound/unbound.conf.d/custom.conf \
  /etc/fail2ban/jail.local \
  /etc/default/pythonfirewall
```

## Support

For issues or questions:
1. Check logs for error messages
2. Verify all services are running
3. Review this guide's troubleshooting section
4. Check GitHub repository issues

## Additional Resources

- Squid Documentation: http://www.squid-cache.org/Doc/
- Unbound Documentation: https://unbound.docs.nlnetlabs.nl/
- UFW Guide: https://help.ubuntu.com/community/UFW
- Fail2ban Wiki: https://www.fail2ban.org/wiki/
- PS5 Network Guide: https://www.playstation.com/support/

## License

This project is provided as-is for personal use. See LICENSE file for details.
