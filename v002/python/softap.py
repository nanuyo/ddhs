import os
import subprocess

# Configuration variables
interface = "wlan0"
ssid = "MySoftAP2"
wpa_passphrase = "password123"

# hostapd configuration
hostapd_conf = f"""
interface={interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={wpa_passphrase}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""

# dnsmasq configuration
dnsmasq_conf = """
interface=wlan0
dhcp-range=192.168.150.2,192.168.150.10,255.255.255.0,24h
"""

# Write hostapd configuration
with open('/etc/hostapd/hostapd.conf', 'w') as f:
    f.write(hostapd_conf)

# Write dnsmasq configuration
with open('/etc/dnsmasq.conf', 'w') as f:
    f.write(dnsmasq_conf)

# Configure network interfaces
interfaces_conf = """
auto lo
iface lo inet loopback

iface eth0 inet dhcp

allow-hotplug wlan0
iface wlan0 inet static
    address 192.168.150.1
    netmask 255.255.255.0
"""

# Write network interfaces configuration
with open('/etc/network/interfaces', 'w') as f:
    f.write(interfaces_conf)

# Enable IP forwarding
with open('/etc/sysctl.conf', 'a') as f:
    f.write("\nnet.ipv4.ip_forward=1\n")

subprocess.run(["sysctl", "-p"], check=True)

# Set up iptables for NAT
subprocess.run(["iptables", "-t", "nat", "-A", "POSTROUTING", "-o", "eth0", "-j", "MASQUERADE"], check=True)
subprocess.run(["sh", "-c", "iptables-save > /etc/iptables/rules.v4"], check=True)

# Restart services
subprocess.run(["systemctl", "restart", "networking"], check=True)
subprocess.run(["systemctl", "unmask", "hostapd"], check=True)
subprocess.run(["systemctl", "enable", "hostapd"], check=True)
subprocess.run(["systemctl", "start", "hostapd"], check=True)
subprocess.run(["systemctl", "restart", "dnsmasq"], check=True)

print("SoftAP setup completed successfully.")
