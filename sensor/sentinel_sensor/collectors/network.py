import psutil
import socket
import httpx
from typing import Dict, Any, List

def collect_network_interfaces() -> Dict[str, Any]:
    """
    Enumerates host network interfaces, private IP assignments, and MAC addresses.
    """
    interfaces = []
    private_ips = []
    mac_addresses = []

    addrs = psutil.net_if_addrs()
    for iface_name, addr_list in addrs.items():
        iface_info = {"name": iface_name, "ipv4": [], "mac": None}
        for addr in addr_list:
            if addr.family == socket.AF_INET:
                iface_info["ipv4"].append(addr.address)
                if not addr.address.startswith("127."):
                    private_ips.append(addr.address)
            elif getattr(psutil, "AF_LINK", None) and addr.family == psutil.AF_LINK:
                iface_info["mac"] = addr.address
                if addr.address:
                    mac_addresses.append(addr.address)
            elif hasattr(socket, "AF_PACKET") and addr.family == socket.AF_PACKET:
                iface_info["mac"] = addr.address
                if addr.address:
                    mac_addresses.append(addr.address)
        interfaces.append(iface_info)

    return {
        "interfaces": interfaces,
        "private_ips": list(set(private_ips)),
        "mac_addresses": list(set(mac_addresses))
    }

async def observe_public_ip() -> str:
    """
    Observes outbound public IP via reliable external gateway.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get("https://api.ipify.org?format=json")
            if res.status_code == 200:
                return res.json().get("ip", "unknown")
    except Exception:
        pass
    return "unknown"
