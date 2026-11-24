import platform
import psutil
from typing import Dict, Any

def collect_system_metrics() -> Dict[str, Any]:
    """
    Collects system hardware telemetry, OS details, and resource utilization.
    """
    cpu_pct = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/') if platform.system() != 'Windows' else psutil.disk_usage('C:\\')

    return {
        "hostname": platform.node(),
        "os_type": platform.system(),
        "os_version": f"{platform.system()} {platform.release()} ({platform.version()})",
        "architecture": platform.machine(),
        "cpu_percent": cpu_pct,
        "memory_percent": mem.percent,
        "disk_percent": disk.percent,
        "boot_time": psutil.boot_time()
    }
