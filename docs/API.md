# SENTINEL SOC — REST API Reference Guide

All Sentinel SOC API endpoints are exposed under `/api/v1` and output standard JSON payloads or formatted CSV streams.

---

## 🔒 Authentication & Tenancy Headers

Except for public authentication endpoints (`/auth/login`, `/auth/register`) and sensor enrollment (`/sensors/enroll`), all API requests require:
```http
Authorization: Bearer <JWT_ACCESS_TOKEN>
X-Organization-Id: <ORGANIZATION_UUID>
```

Sensor telemetry ingestion requires:
```http
X-Sensor-Key: <RAW_SENSOR_API_KEY>
```

---

## 📋 Endpoint Catalog

### 1. Authentication & Multi-Tenancy (`/api/v1/auth`, `/api/v1/organizations`)

- `POST /auth/register`: Create a new user account.
- `POST /auth/login`: Authenticate credentials and receive a JWT access token.
- `GET /auth/me`: Retrieve profile of currently authenticated user.
- `GET /organizations`: List organizations to which the user belongs.
- `POST /organizations`: Create a new organization tenant.
- `GET /organizations/{id}/members`: List tenant members and assigned roles.

---

### 2. Advanced IP Intelligence (`/api/v1/ip-intelligence`)

#### `POST /ip-intelligence/investigate`
Execute an in-depth investigation of an IPv4 or IPv6 address.
```json
// Request Body
{
  "ip_address": "198.51.100.25",
  "notes": "Target observed in failed SSH burst",
  "verdict": "Suspicious"
}
// Response 200 OK
{
  "ip_address": "198.51.100.25",
  "ip_version": "IPv4",
  "classification": "Public",
  "is_routable": true,
  "asn": {
    "asn": "AS15169",
    "org": "Example Transit Corp",
    "country": "US"
  },
  "approximate_geolocation": {
    "country": "United States",
    "city": "Ashburn",
    "notice": "Approximate location only; not an exact physical address"
  },
  "grounding": {
    "directly_observed": { "event_count": 5, "last_observed": "2026-11-16T12:00:00Z" },
    "imported_threat_intel": { "abuseipdb": {...}, "greynoise": {...}, "otx": {...}, "spamhaus": {...} },
    "third_party_enrichment": { "asn": "AS15169", "isp": "Example Corp" },
    "inferred_context": { "risk_heuristic": "Elevated outbound probe volume" },
    "unavailable_telemetry": ["DNS resolution history", "Encrypted payload inspection"]
  },
  "investigation_timeline": [
    { "timestamp": "2026-11-16T11:45:00Z", "event": "Failed SSH authentication" }
  ]
}
```

#### `GET /ip-intelligence/providers`
Query real-time health, cache statistics, and configuration status of external threat feeds (AbuseIPDB, GreyNoise, AlienVault OTX, Spamhaus).

#### `GET /ip-intelligence/investigations`
Retrieve past investigation dossiers and analyst verdicts.

---

### 3. Network Intelligence & Topology (`/api/v1/network`)

#### `GET /network/coverage`
Returns infrastructure visibility metrics:
```json
{
  "total_subnets": 3,
  "monitored_subnets": 2,
  "subnet_coverage_pct": 66.7,
  "total_known_assets": 12,
  "monitored_assets": 8,
  "sensor_coverage_pct": 66.7
}
```

#### `GET /network/topology`
Returns graph nodes and edges strictly distinguishing `OBSERVED` connections (verified via ARP table or socket) from `INFERRED` links (subnet CIDR co-location).

#### `GET /network/integrations` & `POST /network/integrations`
Manage router and gateway adapters (pfSense CE, OPNsense, UniFi, OpenWrt).

#### `POST /network/integrations/{id}/sync`
Initiate on-demand DHCP/ARP metadata synchronization from a registered network gateway.

---

### 4. Advanced Detection & Event Correlation (`/api/v1/detections`)

#### `GET /detections/rules`
List all 13 pre-seeded deterministic and correlation detection rules.

#### `PUT` or `PATCH /detections/rules/{id}/parameters`
Dynamically tune rule threshold and time-window parameters:
```json
// Request Body
{
  "threshold": 10,
  "time_window_seconds": 600
}
```

#### `POST /detections/correlate`
Execute multi-event attack correlation across active alerts and raw security events.

#### `GET /detections/correlations`
List discovered correlated event groups (e.g., multi-asset credential stuffing, brute-force followed by C2 beacon).

---

### 5. Incident Management & Timelines (`/api/v1/incidents`)

#### `GET /incidents/{id}/timeline`
Retrieve the chronological case audit trail (creation, alerts, analyst notes, containment actions).

#### `GET /incidents/{id}/export/csv`
Download the complete case timeline as a standardized CSV file.

#### `POST /incidents/{id}/comments`
Append analyst investigative notes to the incident case.

#### `POST /incidents/{id}/actions/isolate-host`
Execute the host isolation response playbook and log action to the case timeline.

---

### 6. Security Reports & Compliance Exports (`/api/v1/reports`)

- `GET /reports/incidents/csv`: Export all incident cases as CSV.
- `GET /reports/incidents/json`: Export all incident cases as JSON.
- `GET /reports/events/csv`: Export raw security telemetry events as CSV.
- `GET /reports/events/json`: Export raw security telemetry events as JSON.
- `GET /reports/threat-intel/csv`: Export normalized threat indicators database.
- `GET /reports/network/csv`: Export discovered network devices and MAC addresses.
- `GET /reports/aws/csv`: Export AWS security posture findings.
- `GET /reports/summary`: Retrieve executive SOC metrics and incident resolution rates.

---

### 7. AWS Cloud Security Expansion (`/api/v1/aws`)

#### `GET /aws/iam-policy-template`
Retrieve the read-only, least-privilege IAM policy required for cross-account AssumeRole synchronization.

#### `GET /aws/resources`
List discovered cloud assets and configurations.

#### `POST /aws/fixtures/load-all-fixtures`
1-Click seed realistic, zero-cost offline training fixtures (Security Hub, GuardDuty, IAM findings, and S3 resources) without incurring AWS charges.

#### `POST /aws/disconnect`
Cleanly disconnect a registered AWS account and purge cached cloud findings.

---

### 8. Advisory AI Services (`/api/v1/ai-analyst`, `/api/v1/ai-helpdesk`)

#### `POST /ai-analyst/investigate`
Generates a structured 5-part advisory briefing (Facts, Threat Intel, Hypotheses, Recommendations, Unknowns) mapped to MITRE ATT&CK. Operates under human-in-the-loop governance.

#### `POST /ai-helpdesk/chat`
Conversational RAG assistant grounded in Sentinel SOC markdown documentation with automatic credential scrubbing.

---

### 9. Asset Risk Intelligence (`/api/v1/assets`)

#### `GET /assets/{id}/risk`
Retrieve the detailed dynamic risk score breakdown for a specific asset:
```json
{
  "asset_id": "7ce3ec35-62a1-42d9-9b8e-a23bf5e473df",
  "hostname": "workstation-01",
  "risk_score": 65,
  "risk_level": "High",
  "factors": {
    "open_critical_alerts": 1,
    "open_high_alerts": 1,
    "active_incidents": 1,
    "failed_auth_bursts_24h": 6,
    "sensor_health": "Online"
  },
  "score_contributions": {
    "alerts_score": 45,
    "incidents_score": 20,
    "failed_auth_score": 15,
    "health_score": 0
  }
}
```

---

### 10. Automated Response Playbooks & Approvals (`/api/v1/response`)

#### `GET /response/playbooks`
List all pre-seeded enterprise response playbooks (`isolate_endpoint`, `revoke_sensor_credential`, `block_ip_advisory`, `investigation_checklist`, `aws_iam_remediation`).

#### `POST /response/trigger`
Trigger playbook execution against a target entity (asset, IP, sensor, or incident). If the action is destructive, execution status is set to `PENDING_APPROVAL`:
```json
// Request Body
{
  "playbook_key": "isolate_endpoint",
  "target_type": "Asset",
  "target_id": "7ce3ec35-62a1-42d9-9b8e-a23bf5e473df",
  "incident_id": "39d21963-8d3e-457f-96a1-31911f5af77b"
}
```

#### `POST /response/executions/{id}/decision`
Authorizes or rejects an action pending approval:
```json
// Request Body
{
  "decision": "APPROVED", // or "REJECTED"
  "reason": "Host verified compromised via reverse shell C2 beacon."
}
```

---

### 11. Controlled Attack Simulation Lab (`/api/v1/simulation`)

#### `GET /simulation/scenarios`
List all 6 supported simulation scenarios with descriptions and triggered detection rules.

#### `POST /simulation/trigger`
Injects safe synthetic attack events into the active organization with `is_simulated=True`.

#### `POST /simulation/reset`
Atomically purges all simulated events, alerts, and incident cases for the organization while preserving genuine data.

---

### 12. System Administration & RBAC Governance (`/api/v1/admin`)

#### `GET /admin/overview`
System health, database engine, OS/Python environment specs, and runtime telemetry.

#### `GET /admin/users` & `PATCH /admin/users/{user_id}/role`
List organization members and reassign RBAC roles (`Platform Administrator`, `Organization Owner`, `Organization Administrator`, `Security Analyst`, `Viewer`).

#### `GET /admin/integrations`
Returns the operational health matrix for Threat Intel feeds, Cloud Security, Gateways, and AI providers.

#### `GET /admin/retention` & `POST /admin/retention/cleanup`
Inspect retention policies (raw events: 30 days, alerts: 90 days) and trigger on-demand cleanup of expired records.

#### `GET /admin/audit-logs`
Retrieve paginated administrative audit logs recording user identities, IP addresses, and actions.

