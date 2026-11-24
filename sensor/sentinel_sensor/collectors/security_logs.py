import platform
import os
from datetime import datetime
from typing import List, Dict, Any

def collect_security_events() -> List[Dict[str, Any]]:
    """
    Collects operating system security events (authentication failures, privilege events).
    Gracefully handles permissions without crashing.
    """
    events = []
    os_name = platform.system()

    if os_name == "Windows":
        # On Windows, we can query wevtutil or Windows Event Log if running as admin/service
        # For non-admin user development, return cleanly without failure
        pass

    elif os_name == "Linux":
        auth_log_paths = ["/var/log/auth.log", "/var/log/secure"]
        for p in auth_log_paths:
            if os.path.exists(p) and os.access(p, os.R_OK):
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()[-20:]
                        for line in lines:
                            if "failed password" in line.lower() or "authentication failure" in line.lower():
                                events.append({
                                    "event_type": "auth_failure",
                                    "severity": "Medium",
                                    "title": "Local Linux Authentication Failure",
                                    "description": line.strip()[:200],
                                    "raw_payload": {"log_line": line.strip()}
                                })
                except Exception:
                    pass
                break

    return events
