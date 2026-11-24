import asyncio
import logging
from logging.handlers import RotatingFileHandler
import signal
import sys
from datetime import datetime

from sentinel_sensor.config import SensorConfig
from sentinel_sensor.storage import LocalBufferStorage
from sentinel_sensor.client import SensorAPIClient
from sentinel_sensor.collectors.system import collect_system_metrics
from sentinel_sensor.collectors.network import collect_network_interfaces
from sentinel_sensor.collectors.connections import collect_active_connections
from sentinel_sensor.collectors.security_logs import collect_security_events
from sentinel_sensor.collectors.discovery import discover_local_devices

def setup_logger(config: SensorConfig) -> logging.Logger:
    logger = logging.getLogger("sentinel_sensor")
    logger.setLevel(getattr(logging, config.data["logging"]["level"], logging.INFO))
    
    # Rotating file handler
    handler = RotatingFileHandler(
        config.data["logging"]["file_path"],
        maxBytes=config.data["logging"]["max_bytes"],
        backupCount=config.data["logging"]["backup_count"]
    )
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)
    return logger

class SentinelSensorService:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = SensorConfig(config_path)
        self.logger = setup_logger(self.config)
        self.storage = LocalBufferStorage(
            db_path=self.config.data["buffer"]["db_path"],
            max_events=self.config.data["buffer"]["max_buffered_events"]
        )
        self.client = SensorAPIClient(
            server_url=self.config.server_url,
            api_key=self.config.api_key,
            timeout=self.config.data["server"]["timeout_seconds"]
        )
        self.running = False

    async def start(self):
        self.running = True
        self.logger.info("Initializing Sentinel SOC Local Endpoint Sensor...")

        # 1. Check Enrollment
        if not self.config.api_key:
            token = self.config.enrollment_token
            if not token:
                self.logger.error("Sensor has no API key and no enrollment token. Please configure 'enrollment_token' in config.yaml.")
                return
            self.logger.info("Enrolling sensor with token...")
            enroll_res = await self.client.enroll(token)
            if enroll_res.get("success"):
                data = enroll_res["data"]
                self.config.set_credentials(data["sensor_id"], data["api_key"])
                self.client.api_key = data["api_key"]
                self.logger.info(f"Sensor successfully enrolled! Sensor ID: {data['sensor_id']}")
            else:
                self.logger.error(f"Enrollment failed: {enroll_res.get('error')}")
                return

        self.logger.info(f"Sentinel Sensor active and monitoring host. Server: {self.config.server_url}")

        # Start concurrent tasks
        try:
            await asyncio.gather(
                self._heartbeat_loop(),
                self._telemetry_loop(),
                self._buffer_flush_loop()
            )
        except asyncio.CancelledError:
            self.logger.info("Sensor service shutdown requested.")
        finally:
            self.running = False

    async def _heartbeat_loop(self):
        interval = self.config.data["collection"]["heartbeat_interval_seconds"]
        while self.running:
            try:
                metrics = collect_system_metrics()
                conns = collect_active_connections(max_connections=10)
                metrics["active_connections_count"] = len(conns)
                hb_res = await self.client.send_heartbeat(metrics)
                if hb_res.get("success"):
                    self.logger.debug("Heartbeat sent successfully.")
                    for cmd in hb_res.get("commands", []):
                        await self._handle_dispatched_command(cmd)
                else:
                    self.logger.warning("Heartbeat failed (server unreachable).")
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
            await asyncio.sleep(interval)

    async def _handle_dispatched_command(self, cmd: dict):
        cmd_id = cmd.get("id")
        action = cmd.get("action")
        params = cmd.get("params", {})
        self.logger.info(f"Received dispatched command from Sentinel SOC: Action={action}, ID={cmd_id}")

        if not cmd_id or not action:
            self.logger.warning(f"Invalid command format received: {cmd}")
            return

        if action == "DIAGNOSTIC_PROBE":
            self.logger.info(f"Executing non-destructive diagnostic probe: {params}")
            ack = await self.client.acknowledge_command(
                command_id=cmd_id,
                action=action,
                status="SUCCESS",
                details="Diagnostic validation probe executed successfully with zero host modification."
            )
            self.logger.info(f"Command {cmd_id} acknowledged: {ack.get('success')}")

        elif action == "ISOLATE_HOST":
            self.logger.warning(f"ISOLATE_HOST command received (Params: {params}). Performing safe dry-run validation.")
            ack = await self.client.acknowledge_command(
                command_id=cmd_id,
                action=action,
                status="VALIDATED_DRY_RUN",
                details="Network isolation parameters validated. Destructive network drop skipped in safe testing mode."
            )
            self.logger.info(f"Command {cmd_id} acknowledged with dry-run status.")

        else:
            self.logger.warning(f"Unknown or unhandled command action: {action}")
            await self.client.acknowledge_command(
                command_id=cmd_id,
                action=action,
                status="FAILED",
                details=f"Unsupported action: {action}"
            )


    async def _telemetry_loop(self):
        interval = self.config.data["collection"]["telemetry_interval_seconds"]
        while self.running:
            try:
                # 1. Collect Security Events
                events = collect_security_events()
                for ev in events:
                    self.storage.buffer_event("security_event", ev)

                # 2. Collect Active Connections
                conns = collect_active_connections(max_connections=self.config.data["collection"]["max_connections_sample"])

                # 3. Collect Local Discovered Devices
                devices = discover_local_devices() if self.config.data["collection"]["enable_device_discovery"] else []

                # Try sending immediate batch
                success = await self.client.send_telemetry_batch(
                    events=events,
                    discovered_devices=devices,
                    connections=conns
                )
                if success:
                    self.logger.info(f"Telemetry batch dispatched: {len(events)} events, {len(devices)} devices, {len(conns)} conns.")
                else:
                    self.logger.warning("Telemetry delivery failed. Buffered locally for offline resilience.")
            except Exception as e:
                self.logger.error(f"Error in telemetry loop: {e}")
            await asyncio.sleep(interval)

    async def _buffer_flush_loop(self):
        """Flushes locally buffered offline events when connection restores."""
        while self.running:
            try:
                pending_count = self.storage.pending_count()
                if pending_count > 0:
                    self.logger.info(f"Attempting to flush {pending_count} buffered offline events...")
                    batch = self.storage.get_pending_batch(batch_size=50)
                    if batch:
                        buf_ids = [item.pop("_buffer_id") for item in batch]
                        success = await self.client.send_telemetry_batch(
                            events=batch,
                            discovered_devices=[],
                            connections=[]
                        )
                        if success:
                            self.storage.remove_buffered_events(buf_ids)
                            self.logger.info(f"Successfully uploaded {len(buf_ids)} buffered offline events.")
                        else:
                            self.storage.increment_retry(buf_ids)
            except Exception as e:
                self.logger.error(f"Error in buffer flush loop: {e}")
            await asyncio.sleep(60)

    def stop(self):
        self.running = False
        self.logger.info("Stopping Sentinel Sensor service...")

