import argparse
import asyncio
import os
import platform
import sys
import yaml

# Add sensor package to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sentinel_sensor.config import SensorConfig
from sentinel_sensor.client import SensorAPIClient
from sentinel_sensor.service import SentinelSensorService

SYSTEMD_TEMPLATE = """[Unit]
Description=Sentinel SOC Endpoint Monitoring Sensor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={work_dir}
ExecStart={python_exec} {install_script} --run
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

def generate_systemd_service(work_dir: str):
    python_exec = sys.executable
    install_script = os.path.join(work_dir, "install.py")
    service_content = SYSTEMD_TEMPLATE.format(
        work_dir=work_dir,
        python_exec=python_exec,
        install_script=install_script
    )
    service_path = "/etc/systemd/system/sentinel-sensor.service"
    try:
        with open(service_path, "w", encoding="utf-8") as f:
            f.write(service_content)
        print(f"[OK] Systemd service created at {service_path}")
        print("To enable and start the sensor:")
        print("  sudo systemctl daemon-reload")
        print("  sudo systemctl enable --now sentinel-sensor")
    except PermissionError:
        print("[!] Root privileges required to write to /etc/systemd/system/")
        print("Run with sudo, or copy the following unit configuration manually:")
        print(service_content)

def print_windows_service_instructions(work_dir: str):
    python_exec = sys.executable
    install_script = os.path.join(work_dir, "install.py")
    print("\n--- Windows Service Installation Guide ---")
    print("Method 1: Run in background via Windows Scheduled Task (No 3rd party tools required):")
    print(f'  schtasks /create /tn "SentinelSensor" /tr "\"{python_exec}\" \"{install_script}\" --run" /sc onstart /ru SYSTEM')
    print("\nMethod 2: Run via NSSM (Non-Sucking Service Manager):")
    print(f'  nssm install SentinelSensor "{python_exec}" "{install_script}" --run')
    print('  nssm set SentinelSensor AppDirectory "' + work_dir + '"')
    print('  nssm start SentinelSensor')
    print("------------------------------------------\n")

async def enroll_cli(token: str, server_url: str):
    config = SensorConfig()
    config.data["server"]["url"] = server_url
    timeout = float(config.data["server"].get("timeout_seconds", 60))
    client = SensorAPIClient(server_url=server_url, timeout=timeout)
    print(f"Connecting to Sentinel SOC at {server_url} with enrollment token: [REDACTED_TOKEN]")
    res = await client.enroll(token)
    if res.get("success"):
        data = res["data"]
        config.set_credentials(data["sensor_id"], data["api_key"])
        print(f"[SUCCESS] Sensor successfully enrolled!")
        print(f"  Sensor ID: {data['sensor_id']}")
        print(f"  Asset ID:  {data['asset_id']}")
        print(f"  Status:    {data['status']}")
        print(f"Credentials saved to {config.config_path}")
    else:
        print(f"[ERROR] Enrollment failed: {res.get('error') or res}")

def main():
    parser = argparse.ArgumentParser(description="Sentinel SOC Sensor Installer & Runner")
    parser.add_argument("--enroll", type=str, help="Enrollment token to register this endpoint")
    parser.add_argument("--server", type=str, default="http://localhost:8000", help="Sentinel SOC API Server URL")
    parser.add_argument("--run", action="store_true", help="Run the sensor service in foreground")
    parser.add_argument("--setup-service", action="store_true", help="Install systemd or Windows background service")

    args = parser.parse_args()
    work_dir = os.path.dirname(os.path.abspath(__file__))

    if args.enroll:
        asyncio.run(enroll_cli(args.enroll, args.server))
    elif args.setup_service:
        if platform.system() == "Linux":
            generate_systemd_service(work_dir)
        else:
            print_windows_service_instructions(work_dir)
    elif args.run:
        service = SentinelSensorService()
        try:
            asyncio.run(service.start())
        except KeyboardInterrupt:
            service.stop()
            print("\nSensor stopped by operator.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
