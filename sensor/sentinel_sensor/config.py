import os
import yaml
from typing import Dict, Any

class SensorConfig:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.data: Dict[str, Any] = {
            "server": {"url": "http://localhost:8000", "verify_ssl": True, "timeout_seconds": 15},
            "auth": {"enrollment_token": "", "sensor_id": "", "api_key": ""},
            "collection": {
                "heartbeat_interval_seconds": 30,
                "telemetry_interval_seconds": 60,
                "enable_device_discovery": True,
                "enable_security_logs": True,
                "enable_connection_monitoring": True,
                "max_connections_sample": 50
            },
            "buffer": {"db_path": "sentinel_sensor_buffer.db", "max_buffered_events": 10000, "batch_size": 50},
            "logging": {"level": "INFO", "file_path": "sentinel_sensor.log", "max_bytes": 5242880, "backup_count": 3}
        }
        self.load()

    def _resolve_config_path(self, path: str) -> str:
        if os.path.isabs(path) and os.path.exists(path):
            return path
        # 1. Current working directory
        if os.path.exists(path):
            return os.path.abspath(path)
        # 2. Sensor module directory
        sensor_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sensor_candidate = os.path.join(sensor_dir, path)
        if os.path.exists(sensor_candidate):
            return sensor_candidate
        # 3. Project root directory
        root_dir = os.path.dirname(sensor_dir)
        root_candidate = os.path.join(root_dir, path)
        if os.path.exists(root_candidate):
            return root_candidate
        return path

    def load(self):
        resolved = self._resolve_config_path(self.config_path)
        if os.path.exists(resolved):
            self.config_path = resolved
            with open(resolved, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if loaded:
                    for k, v in loaded.items():
                        if isinstance(v, dict) and k in self.data:
                            self.data[k].update(v)
                        else:
                            self.data[k] = v

    def save(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self.data, f, default_flow_style=False)

    @property
    def server_url(self) -> str:
        return self.data["server"]["url"].rstrip("/")

    @property
    def api_key(self) -> str:
        return self.data["auth"].get("api_key", "")

    @property
    def sensor_id(self) -> str:
        return self.data["auth"].get("sensor_id", "")

    @property
    def enrollment_token(self) -> str:
        return self.data["auth"].get("enrollment_token", "")

    def set_credentials(self, sensor_id: str, api_key: str):
        self.data["auth"]["sensor_id"] = sensor_id
        self.data["auth"]["api_key"] = api_key
        self.data["auth"]["enrollment_token"] = ""  # Clear enrollment token once registered
        self.save()
