import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal, engine, Base
import backend.app.models
from backend.app.config import settings
from backend.app.core.security import hash_password, hash_token, generate_sensor_api_key
from backend.app.core.detection_engine import seed_default_detection_rules
from backend.app.models.auth import User, Organization, OrganizationMembership, AuditLog
from backend.app.models.assets import Asset, Sensor, SensorHeartbeat
from backend.app.models.network import Network, NetworkDevice, IPAddress, IPObservation
from backend.app.models.events import SecurityEvent, ThreatIndicator
from backend.app.models.detections import DetectionResult
from backend.app.models.incidents import Incident, IncidentEvent, IncidentComment
from backend.app.models.response import ResponsePlaybook

def ensure_schema_migrations():
    """Ensures newly added columns exist in SQLite/Postgres database if not present."""
    from sqlalchemy import text
    try:
        # SQLite dialect-specific column checks
        if engine.dialect.name == "sqlite":
            with engine.connect() as conn:
                res = conn.execute(text("PRAGMA table_info(incidents)"))
                cols = [row[1] for row in res.fetchall()]
                if cols and "is_simulated" not in cols:
                    conn.execute(text("ALTER TABLE incidents ADD COLUMN is_simulated BOOLEAN DEFAULT 0 NOT NULL"))
                    conn.commit()

                # Assets table migration for risk_score
                res_assets = conn.execute(text("PRAGMA table_info(assets)"))
                cols_assets = [row[1] for row in res_assets.fetchall()]
                if cols_assets and "risk_score" not in cols_assets:
                    conn.execute(text("ALTER TABLE assets ADD COLUMN risk_score INTEGER DEFAULT 15 NOT NULL"))
                    conn.commit()

                # Sensors table migration for pending_commands
                res_sensors = conn.execute(text("PRAGMA table_info(sensors)"))
                cols_sensors = [row[1] for row in res_sensors.fetchall()]
                if cols_sensors and "pending_commands" not in cols_sensors:
                    conn.execute(text("ALTER TABLE sensors ADD COLUMN pending_commands TEXT NULL"))
                    conn.commit()
    except Exception as e:
        print(f"Schema migration check note: {e}")

def seed_database():
    ensure_schema_migrations()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if already seeded
        existing_user = db.query(User).filter(User.email == "admin@sentinelsoc.com").first()
        if existing_user:
            print("Database already contains seed user. Ensuring detection rules...")
            seed_default_detection_rules(db)
            return

        print("Seeding Sentinel SOC database with initial structure and demo data...")
        now = datetime.utcnow()

        # 1. Create Default Admin User
        admin_user = User(
            email="admin@sentinelsoc.com",
            hashed_password=hash_password("SentinelAdmin123!"),
            full_name="Chief Information Security Officer",
            is_active=True,
            is_platform_admin=True
        )
        db.add(admin_user)
        db.flush()

        # 2. Create Primary Organization
        primary_org = Organization(
            name="Global Defense SOC",
            slug="global-defense-soc",
            is_active=True
        )
        db.add(primary_org)
        db.flush()

        # 3. Create Membership
        membership = OrganizationMembership(
            user_id=admin_user.id,
            organization_id=primary_org.id,
            role="Organization Owner"
        )
        db.add(membership)

        # 4. Seed Default Detection Rules
        seed_default_detection_rules(db)

        # 5. Seed Threat Intelligence Indicators
        indicators = [
            ThreatIndicator(
                indicator_type="IPv4",
                indicator_value="185.220.101.5",
                threat_type="Tor Exit / Reconnaissance Node",
                severity="Critical",
                source="AbuseIPDB Verified Feed",
                description="Known active malicious scanner and Tor egress node reported for brute-force SSH attacks.",
                confidence=95
            ),
            ThreatIndicator(
                indicator_type="IPv4",
                indicator_value="194.26.29.112",
                threat_type="Mass Network Scanner",
                severity="High",
                source="GreyNoise Intelligence",
                description="Observed scanning global internet IPv4 space for exposed RDP (port 3389) and SSH (port 22).",
                confidence=90
            ),
            ThreatIndicator(
                indicator_type="IPv4",
                indicator_value="45.33.32.156",
                threat_type="C2 Beaconing Target",
                severity="High",
                source="AlienVault OTX Community",
                description="Identified in adversary infrastructure campaigns as active HTTP/S beacon receptor.",
                confidence=85
            )
        ]
        db.add_all(indicators)

        # 6. Seed Sample Assets
        asset_srv = Asset(
            organization_id=primary_org.id,
            hostname="prod-core-db01",
            os_family="Linux",
            os_version="Ubuntu 22.04 LTS",
            asset_type="Server",
            private_ips=json.dumps(["192.168.1.10"]),
            mac_addresses=json.dumps(["00:50:56:A1:B2:C3"]),
            public_ip="203.0.113.15",
            health_status="online",
            risk_level="Medium",
            last_seen=now
        )
        asset_ws = Asset(
            organization_id=primary_org.id,
            hostname="fin-ws-alice",
            os_family="Windows",
            os_version="Windows 11 Pro 23H2",
            asset_type="Endpoint",
            private_ips=json.dumps(["192.168.1.45"]),
            mac_addresses=json.dumps(["B4:2E:99:12:34:56"]),
            health_status="online",
            risk_level="Low",
            last_seen=now
        )
        db.add_all([asset_srv, asset_ws])
        db.flush()

        # 7. Seed Enrolled Sensor for the Linux Server (Demo Asset)
        is_production = settings.ENVIRONMENT.lower() == "production"
        if is_production:
            # Production guard: Never seed predictable credentials into production database.
            # Sensor is created as inactive with no usable API key hash.
            api_key_hash_val = None
        else:
            # Development / testing credential only
            api_key_raw = "sak_seed_sample_key_for_linux_sensor"
            api_key_hash_val = hash_token(api_key_raw)

        sensor_linux = Sensor(
            organization_id=primary_org.id,
            asset_id=asset_srv.id,
            name="prod-db01-agent",
            os_type="Linux",
            version="1.0.0",
            status="Online" if not is_production else "Offline",
            is_token_used=True,
            api_key_hash=api_key_hash_val,
            capabilities=json.dumps({"system_metrics": "Available", "connections": "Available", "security_logs": "Available", "discovery": "Available"}),
            last_heartbeat=now
        )
        db.add(sensor_linux)
        db.flush()

        # Heartbeat sample
        hb = SensorHeartbeat(
            sensor_id=sensor_linux.id,
            timestamp=now,
            cpu_percent=14.2,
            memory_percent=42.8,
            disk_percent=31.0,
            active_connections_count=18,
            status="Online",
            metadata_json=json.dumps({"kernel": "5.15.0-generic"})
        )
        db.add(hb)

        # 8. Seed Network & Devices
        net = Network(
            organization_id=primary_org.id,
            name="HQ Corporate LAN",
            cidr="192.168.1.0/24",
            network_type="Corporate LAN",
            observation_source="Sensor Discovery",
            is_authorized=True
        )
        db.add(net)
        db.flush()

        devices = [
            NetworkDevice(
                organization_id=primary_org.id,
                network_id=net.id,
                ip_address="192.168.1.1",
                mac_address="00:11:22:33:44:55",
                hostname="gw-cisco-core01",
                vendor="Cisco Systems",
                device_type="Router",
                is_authorized=True,
                first_seen=now - timedelta(days=30),
                last_seen=now
            ),
            NetworkDevice(
                organization_id=primary_org.id,
                network_id=net.id,
                ip_address="192.168.1.10",
                mac_address="00:50:56:A1:B2:C3",
                hostname="prod-core-db01",
                vendor="VMware",
                device_type="Server",
                is_authorized=True,
                first_seen=now - timedelta(days=20),
                last_seen=now
            ),
            NetworkDevice(
                organization_id=primary_org.id,
                network_id=net.id,
                ip_address="192.168.1.45",
                mac_address="B4:2E:99:12:34:56",
                hostname="fin-ws-alice",
                vendor="Dell Inc.",
                device_type="Workstation",
                is_authorized=True,
                first_seen=now - timedelta(days=10),
                last_seen=now
            ),
            NetworkDevice(
                organization_id=primary_org.id,
                network_id=net.id,
                ip_address="192.168.1.188",
                mac_address="00:1A:2B:3C:4D:EE",
                hostname="unauthorized-rpi-lan",
                vendor="Raspberry Pi Foundation",
                device_type="Unknown",
                is_authorized=False,
                first_seen=now - timedelta(hours=2),
                last_seen=now
            )
        ]
        db.add_all(devices)

        # 9. Seed Security Events
        events = [
            SecurityEvent(
                organization_id=primary_org.id,
                asset_id=asset_srv.id,
                sensor_id=sensor_linux.id,
                event_type="auth_failure",
                severity="Medium",
                title="Repeated SSH Authentication Failure",
                description="Observed failed password attempts for user 'ubuntu' from external IP 185.220.101.5",
                source_ip="185.220.101.5",
                destination_ip="192.168.1.10",
                source_port=52341,
                destination_port=22,
                protocol="TCP",
                is_simulated=False,
                timestamp=now - timedelta(minutes=45),
                created_at=now
            ),
            SecurityEvent(
                organization_id=primary_org.id,
                asset_id=asset_srv.id,
                sensor_id=sensor_linux.id,
                event_type="network_connection",
                severity="Critical",
                title="Connection with Known Malicious Threat Indicator",
                description="Inbound TCP session initiated from verified Tor exit node 185.220.101.5",
                source_ip="185.220.101.5",
                destination_ip="192.168.1.10",
                source_port=49112,
                destination_port=22,
                protocol="TCP",
                is_simulated=False,
                timestamp=now - timedelta(minutes=40),
                created_at=now
            ),
            SecurityEvent(
                organization_id=primary_org.id,
                asset_id=asset_ws.id,
                event_type="process_exec",
                severity="Informational",
                title="Legitimate System Process Execution",
                description="PowerShell process launched with signed script execution policy.",
                source_ip="192.168.1.45",
                protocol="LOCAL",
                is_simulated=False,
                timestamp=now - timedelta(hours=3),
                created_at=now
            )
        ]
        db.add_all(events)
        db.flush()

        # 10. Seed Detection Result & Incident
        det = DetectionResult(
            organization_id=primary_org.id,
            rule_name="Connection to Known Malicious Threat Indicator",
            severity="Critical",
            title="External Scan & Login Burst from 185.220.101.5",
            description="Matched Threat Indicator AbuseIPDB. Target: prod-core-db01 on SSH port 22.",
            evidence_json=json.dumps({"source_ip": "185.220.101.5", "target_host": "prod-core-db01", "port": 22}),
            confidence=95,
            related_asset_id=asset_srv.id,
            related_ip="185.220.101.5",
            is_simulated=False,
            status="Open",
            timestamp=now - timedelta(minutes=35)
        )
        db.add(det)
        db.flush()

        inc = Incident(
            organization_id=primary_org.id,
            title="Investigate Inbound Brute-Force from Tor Node 185.220.101.5",
            description="Multiple failed SSH authentications followed by connection from verified malicious IP 185.220.101.5 against database server prod-core-db01.",
            severity="High",
            status="Investigating",
            assigned_to_user_id=admin_user.id,
            related_asset_ids_json=json.dumps([asset_srv.id]),
            related_ip_addresses_json=json.dumps(["185.220.101.5"]),
            created_at=now - timedelta(minutes=30)
        )
        db.add(inc)
        db.flush()

        inc_ev = IncidentEvent(
            incident_id=inc.id,
            security_event_id=events[1].id,
            detection_result_id=det.id,
            added_at=now
        )
        db.add(inc_ev)

        comment = IncidentComment(
            incident_id=inc.id,
            user_id=admin_user.id,
            user_name=admin_user.full_name,
            comment="Initial triage: Verified source IP is an active Tor egress node. Target port is SSH. No successful logins detected in auth log.",
            is_ai_generated=False,
            created_at=now - timedelta(minutes=20)
        )
        db.add(comment)

        # Seed Response Playbooks
        pb1 = ResponsePlaybook(
            organization_id=primary_org.id,
            name="Isolate Host from Network",
            description="Requests endpoint containment by restricting local network traffic except Sentinel management communication.",
            action_type="isolate_endpoint",
            requires_approval=True,
            is_enabled=True,
            created_at=now
        )
        pb2 = ResponsePlaybook(
            organization_id=primary_org.id,
            name="Revoke Compromised Sensor Credential",
            description="Revokes active sensor API key and terminates ingestion privileges.",
            action_type="revoke_sensor_credential",
            requires_approval=True,
            is_enabled=True,
            created_at=now
        )
        db.add_all([pb1, pb2])

        db.commit()
        print("Sentinel SOC database seeded successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
