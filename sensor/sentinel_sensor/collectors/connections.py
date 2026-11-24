import psutil
from typing import List, Dict, Any

def collect_active_connections(max_connections: int = 50) -> List[Dict[str, Any]]:
    """
    Collects active TCP and UDP sockets with remote addresses, ports, and associated process.
    """
    connections = []
    try:
        conns = psutil.net_connections(kind='inet')
        for c in conns:
            # We filter for established or syn sockets, or connections with remote addresses
            if c.raddr:
                proc_name = "unknown"
                if c.pid:
                    try:
                        p = psutil.Process(c.pid)
                        proc_name = p.name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        proc_name = "restricted"

                connections.append({
                    "local_ip": c.laddr.ip,
                    "local_port": c.laddr.port,
                    "destination_ip": c.raddr.ip,
                    "destination_port": c.raddr.port,
                    "status": c.status,
                    "protocol": "TCP" if c.type == 1 else "UDP",
                    "direction": "Outbound",
                    "pid": c.pid,
                    "process_name": proc_name
                })
                if len(connections) >= max_connections:
                    break
    except (psutil.AccessDenied, Exception):
        pass
    return connections
