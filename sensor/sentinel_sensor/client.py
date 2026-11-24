import platform
import httpx
from typing import Dict, Any, List, Optional

class SensorAPIClient:
    def __init__(self, server_url: str, api_key: Optional[str] = None, timeout: float = 60.0):
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-Sensor-Key"] = self.api_key
        return headers

    async def enroll(self, enrollment_token: str) -> Dict[str, Any]:
        url = f"{self.server_url}/api/v1/sensors/enroll"
        payload = {
            "enrollment_token": enrollment_token,
            "hostname": platform.node(),
            "os_type": platform.system(),
            "os_version": f"{platform.system()} {platform.release()}",
            "capabilities": {
                "system_metrics": "Available",
                "connections": "Available",
                "security_logs": "Available",
                "device_discovery": "Available"
            }
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(url, json=payload)
            if res.status_code == 200:
                data = res.json()
                self.api_key = data.get("api_key")
                return {"success": True, "data": data}
            return {"success": False, "status_code": res.status_code, "error": res.text}

    async def send_heartbeat(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            return {"success": False, "commands": []}
        url = f"{self.server_url}/api/v1/sensors/heartbeat"
        payload = {
            "cpu_percent": metrics.get("cpu_percent"),
            "memory_percent": metrics.get("memory_percent"),
            "disk_percent": metrics.get("disk_percent"),
            "active_connections_count": metrics.get("active_connections_count", 0),
            "metadata": {"hostname": metrics.get("hostname")}
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=payload, headers=self._get_headers())
                if res.status_code == 200:
                    data = res.json()
                    return {"success": True, "commands": data.get("dispatched_commands", []), "status_code": 200}
                return {"success": False, "commands": [], "status_code": res.status_code}
        except Exception:
            return {"success": False, "commands": [], "status_code": 0}

    async def acknowledge_command(
        self,
        command_id: str,
        action: str,
        status: str = "SUCCESS",
        details: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.api_key:
            return {"success": False, "error": "No API key"}
        url = f"{self.server_url}/api/v1/sensors/commands/acknowledge"
        payload = {
            "command_id": command_id,
            "action": action,
            "status": status,
            "details": details
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=payload, headers=self._get_headers())
                if res.status_code == 200:
                    return {"success": True, "data": res.json()}
                return {"success": False, "status_code": res.status_code, "error": res.text}
        except Exception as e:
            return {"success": False, "error": str(e)}


    async def send_telemetry_batch(
        self,
        events: List[Dict[str, Any]],
        discovered_devices: List[Dict[str, Any]],
        connections: List[Dict[str, Any]]
    ) -> bool:
        if not self.api_key:
            return False
        url = f"{self.server_url}/api/v1/sensors/telemetry"
        payload = {
            "sensor_version": "1.0.0",
            "events": events,
            "discovered_devices": discovered_devices,
            "active_connections_sample": connections
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=payload, headers=self._get_headers())
                return res.status_code == 200
        except Exception:
            return False

