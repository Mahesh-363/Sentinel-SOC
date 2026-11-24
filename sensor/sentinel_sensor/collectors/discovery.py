import re
import subprocess
import platform
from typing import List, Dict, Any

def discover_local_devices() -> List[Dict[str, Any]]:
    """
    Passively inspects host ARP cache for observed neighbors on local subnet.
    Safe, non-destructive, and strictly confined to already communicated devices.
    """
    devices = []
    try:
        output = subprocess.check_output(["arp", "-a"], stderr=subprocess.DEVNULL, text=True, timeout=5)
        # Parse ARP lines
        # Windows: "  192.168.1.1           00-11-22-33-44-55     dynamic"
        # Linux: "? (192.168.1.1) at 00:11:22:33:44:55 [ether] on eth0"
        for line in output.splitlines():
            ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
            mac_match = re.search(r'([0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2})', line)
            
            if ip_match and mac_match:
                ip = ip_match.group(1)
                mac = mac_match.group(1).replace('-', ':').upper()
                
                # Exclude broadcast and multicast addresses
                if not (ip.endswith(".255") or ip.startswith("224.") or ip.startswith("239.") or mac == "FF:FF:FF:FF:FF:FF"):
                    devices.append({
                        "ip_address": ip,
                        "mac_address": mac,
                        "hostname": None,
                        "vendor": "Observed via ARP",
                        "device_type": "Workstation" if not ip.endswith(".1") else "Router"
                    })
    except Exception:
        pass
    return devices
