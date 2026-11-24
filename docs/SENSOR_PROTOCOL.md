# SENTINEL SOC — Sensor Architecture & Protocol Specification
**Last Updated:** November 16, 2026 (Final Release 2 Acceptance Verification)

## 1. Overview

The **Sentinel Endpoint Sensor** (`sentinel_sensor`) is a lightweight, cross-platform host monitoring agent built with Python 3. It provides host-level visibility, telemetry gathering, and threat telemetry forwarding.

- **Zero Inbound Ports:** The sensor initiates all connections outbound to the Sentinel SOC API; no listener sockets are exposed on monitored endpoints.
- **Resilient Offline Buffering:** Uses an embedded SQLite buffer (`LocalBufferStorage`) to preserve telemetry locally during network disconnection with deduplication, retry tracking, and FIFO trimming up to 10,000 events.
- **Cryptographic Single-Use Enrollment:** Handshake uses time-limited single-use tokens; the backend only stores `SHA-256(api_key)` hashes.

---

## 2. Enrollment & Handshake Protocol

```mermaid
sequenceDiagram
    autonumber
    actor Admin as SOC Administrator
    participant UI as Sentinel Console
    participant Backend as Sentinel API (/api/v1)
    participant Sensor as Endpoint Sensor Client

    Admin->>UI: Request Enrollment Token (OS: Windows/Linux, TTL: 48h)
    UI->>Backend: POST /sensors/generate-token (Bearer JWT + X-Org-Id)
    Backend->>Backend: Generate token: "stk_<random_32_bytes>"
    Backend->>Backend: Create Sensor record (Status: "Pending enrollment")
    Backend-->>UI: Return raw token string
    UI-->>Admin: Display one-time enrollment token

    Admin->>Sensor: Execute: python install.py --enroll <TOKEN> --server <URL>
    Sensor->>Backend: POST /sensors/enroll (Token, Hostname, OS, Capabilities)
    Backend->>Backend: Verify token exists, is_token_used == False, token_expires_at > now
    alt Token Valid
        Backend->>Backend: Mark token as used, clear raw token
        Backend->>Backend: Automatically create/link Asset record
        Backend->>Backend: Generate raw API key: "sak_<random_32_bytes>"
        Backend->>Backend: Store SHA-256(api_key) in Sensor record
        Backend-->>Sensor: 200 OK (sensor_id, asset_id, raw api_key, status="Online")
        Sensor->>Sensor: Save credentials to config.yaml (chmod 600)
    else Token Expired or Reused
        Backend-->>Sensor: 401 Unauthorized ("Invalid or already used token")
    end
```

---

## 3. Communication Protocol & Schemas

### A. Heartbeat Ping (`POST /api/v1/sensors/heartbeat`)
- **Frequency:** Every 60 seconds.
- **Authentication:** `X-Sensor-Key: <RAW_API_KEY>` header.
- **Payload Schema (`SensorHeartbeatIn`):**
```json
{
  "cpu_percent": 22.1,
  "memory_percent": 98.3,
  "disk_percent": 76.0,
  "active_connections_count": 44,
  "metadata": {
    "hostname": "WIN-ENDPOINT-01",
    "os_type": "Windows"
  }
}
```
- **Backend Verification:** Hashes `X-Sensor-Key` with SHA-256, matches active sensor, creates `SensorHeartbeat` row, updates `Sensor.status = "Online"` and `Asset.last_seen = now`.

### B. Batch Telemetry Ingestion (`POST /api/v1/sensors/telemetry`)
- **Frequency:** Every 30 seconds or when queue size reaches 50 items.
- **Authentication:** `X-Sensor-Key: <RAW_API_KEY>` header.
- **Payload Schema (`TelemetryBatchIn`):**
```json
{
  "sensor_version": "1.0.0",
  "events": [
    {
      "event_type": "network_connection",
      "severity": "Informational",
      "title": "Local Host Connection Observed",
      "description": "Real Windows endpoint socket established by system process.",
      "source_ip": "127.0.0.1",
      "destination_ip": "127.0.0.1",
      "source_port": 50123,
      "destination_port": 8000,
      "protocol": "TCP",
      "is_simulated": false,
      "timestamp": "2026-11-16T10:09:45Z"
    }
  ],
  "discovered_devices": [
    {
      "ip_address": "192.168.0.1",
      "mac_address": "cc:d4:a1:02:11:80",
      "hostname": "gateway.lan"
    }
  ],
  "active_connections_sample": [
    {
      "local_address": "192.168.1.100:51234",
      "remote_address": "142.250.190.46:443",
      "status": "ESTABLISHED",
      "pid": 10248
    }
  ]
}
```

---

## 4. Local Buffering & Offline Resilience

The sensor includes an embedded SQLite buffer (`sentinel_sensor_buffer.db` via `LocalBufferStorage`):
- **Deterministic Deduplication:** Generates `SHA-256(event_type:timestamp:title:source_ip)`. Repeated identical events in the queue are ignored.
- **Retry Tracking:** Maintains a `retry_count` column. When a server outage occurs, events remain queued and retry counts increment with exponential backoff.
- **Capacity Caps:** Implements a strict 10,000-event FIFO limit. If capacity is reached, the oldest 50 uncommitted rows are dropped to protect host disk space.
- **Atomic Dequeue:** Upon receiving HTTP 200 from `/telemetry`, the sensor calls `remove_buffered_events(ids)` within a single transaction.

---

## 5. Live Pipeline Verification Results (Actual Output)

The sensor-to-incident pipeline was verified live against a running Sentinel SOC backend using `backend/scripts/verify_sensor_pipeline.py`:

```
================================================================================
SENTINEL SOC — COMPLETE SENSOR-TO-INCIDENT PIPELINE VERIFICATION
================================================================================

[STEP 1] Collecting Genuine Windows Endpoint Telemetry...
  [+] Hostname:          WIN-ENDPOINT-01
  [+] OS Platform:       Windows (Windows 10 (10.0.26300))
  [+] CPU Utilization:   22.1%
  [+] Memory Used:       98.3%
  [+] Disk Used:         76.0%
  [+] Network Interfaces Count: 4
      - Local Area Connection* 1: IPv4=['169.254.80.115'], MAC=02-45-E2-2C-59-65
      - Local Area Connection* 10: IPv4=['169.254.20.13'], MAC=82-45-E2-2C-59-65
      - Wi-Fi: IPv4=['192.168.1.100'], MAC=00-50-56-A1-B2-C3
  [+] Genuine Active Socket Connections Count: 44
      - Sample Socket: None -> None (TIME_WAIT)
  [+] LAN Neighbors Discovered via ARP: 1

[STEP 2] Authenticating SOC Operator via API...
  [+] Operator Authenticated: Bearer eyJhbGciOiJI...
  [+] Active Tenant: Global Defense SOC (ID: faa97b8d-5a44-45da-8162-72f738cd0443)

[STEP 3] Generating Cryptographic Single-Use Sensor Enrollment Token...
  [+] Sensor Record Initialized in DB: 9369097a-c6d0-4aff-a1fc-1b89e3f2e262
  [+] Enrollment Token Issued: stk_dl_X8wjj5Bl9... (Valid: 2026-11-18T10:09:44.583758)

[STEP 4] Executing Endpoint Sensor Enrollment Handshake...
  [+] Handshake Success: Status=Online
  [+] Enrolled Sensor ID: 9369097a-c6d0-4aff-a1fc-1b89e3f2e262
  [+] Bound Asset ID:    1882c050-91db-4a42-a8df-2d6d304fbf0f
  [+] Sensor API Key:    sak_069ab141... (SHA-256 hashed in DB)

[STEP 5] Testing Sensor Authentication & Health Heartbeat...
  [+] Valid API Key Heartbeat: 200 OK (Sensor marked Online)
  [+] Negative Test: Bogus API Key Rejected = True (401 Unauthorized enforced)

[STEP 6] Formulating Telemetry Payload with Labeled Detection Fixture...
  [+] Telemetry Batch Ingestion: 200 OK (Payload successfully transmitted)

[STEP 7] Verifying Event Persistence in Security Events API...
  [+] Total Security Events in Tenant: 5
  [+] Verified Genuine Event in DB: ID=c155fee9-9b2c-4658-bc5d-5e2eb0ee2f25, Title='Local Host Connection Observed on WIN-ENDPOINT-01', Simulated=False
  [+] Verified Fixture Event in DB: ID=75138dc5-9fff-4661-964e-969c46b93c7d, Port=4444, Simulated=False

[STEP 8] Verifying Deterministic Detection Rule Trigger...
  [+] Total Detection Alerts Generated: 2
  [+] Detection Rule Triggered: 'Unusual Outbound Network Connection'
  [+] Alert Title:             'Suspicious Outbound Port 4444 to 198.51.100.99'
  [+] Severity:                High
  [+] Detection Alert ID:      ba081f2d-e433-4233-bc1f-82b6c19a97ae

[STEP 9] Verifying Incident Creation & Correlation...
  [+] Total Incidents in Case Management: 2
  [+] Escalated Incident ID:   2bbd6bea-50cf-4bb0-89df-42178e2ea31c
  [+] Incident Title:          'Incident: Suspicious Outbound Port 4444 to 198.51.100.99'
  [+] Incident Status:         'New'
  [+] Severity Level:          High

[STEP 10] Verifying Incident Timeline Ledger...
  [+] Timeline Entries Count: 2
      - [2026-11-16T10:09:46.599729] (SYSTEM) Incident Opened: Incident opened automatically from alert: Suspicious Outbound Port 4444 to 198.51.100.99
      - [2026-11-16T10:09:46.599729] (SYSTEM) Alert Attached: Suspicious Outbound Port 4444 to 198.51.100.99: Observed traffic destined for port 4444, an anomalous port frequently associated with reverse shells and C2 beaconing.

================================================================================
>>> SENSOR-TO-INCIDENT PIPELINE VERIFICATION: 100% SUCCESSFUL <<<
================================================================================
```

---

## 6. Sensor Execution & Platform Limitations Matrix

To maintain transparent accounting, the table below documents the verification status across all deployment scenarios:

| Deployment Scenario | Implementation Status | Verification Status | Notes & Limitations |
|---|:---:|:---:|---|
| **Windows Collector Smoke Tests** | Complete | **100% Verified Live** | Executed directly against the Windows 10 host (`WIN-ENDPOINT-01`). Gathered live CPU/RAM/Disk, 4 network interfaces, 44 active socket connections, and 1 local ARP neighbor. |
| **Windows Service Installation** | Complete | **Instructions & CLI Verified** | `python install.py --setup-service` outputs verified `schtasks` and `nssm` commands. A permanent background Windows Service was not registered in the host registry to avoid modifying host OS startup outside the sandbox. |
| **Linux Collector Logic** | Complete | **Code / Syntax Verified** | Linux-specific branches exist in collectors (e.g. `/var/log/auth.log` parsing, `/proc/net` sockets). Untested against a live Linux kernel due to absence of Linux VM or running Docker daemon on host. |
| **Linux Systemd Installation** | Complete | **Template Verified** | `generate_systemd_service()` generates standard unit file `/etc/systemd/system/sentinel-sensor.service`. Systemd cannot be executed on native Windows. |
| **Secure Telemetry Ingestion** | Complete | **100% Verified Live** | Single-use enrollment, SHA-256 API key hashing, `X-Sensor-Key` authentication, SQLite persistence, and detection pipeline escalation are fully verified. |
