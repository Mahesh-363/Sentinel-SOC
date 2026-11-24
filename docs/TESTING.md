# SENTINEL SOC — Testing & Quality Assurance Guide
**Last Updated:** November 16, 2026 (Final Engineering Audit & Security Hardening)

Sentinel SOC utilizes a multi-tier testing and verification framework to ensure backend reliability, frontend stability, sensor resilience, and data isolation.

---

## 🔍 Testing Taxonomy & Verification Scope

To maintain engineering transparency, all automated and manual tests are categorized according to their execution context:

| Test Category | Framework / Tool | Test Target | Execution Context | Verification Depth |
|---|---|---|---|---|
| **Backend Unit & API Tests** | Pytest + HTTPX | FastAPI routers, ORM models, detection rules, auth, risk engine, sensor command queues, audit logs, health ping & trusted proxies. | Live test DB (SQLite in-memory/file). | **25 test items across 13 test files** executing against real endpoints and database queries. |
| **Frontend E2E Tests** | Playwright (Chromium) | Next.js 14 views, navigation, forms, modals, error alerts. | Mocked backend API (`page.route`). | **15 E2E browser tests** verifying UI rendering, form submission, and client error handling in isolation. |
| **Live Sensor Pipeline** | Python async script | Genuine Windows telemetry, enrollment, heartbeats, detection, case creation. | Live running backend + Windows host. | **12-step end-to-end integration** testing genuine OS APIs, database storage, and isolation teardown. |
| **Response Automation Lifecycle** | Python async script | Playbook invocation, approval gate, sensor command queue, heartbeat polling, ack. | Live running backend + enrolled sensor. | **9-step end-to-end lifecycle** verifying approval enforcement, command dispatch, and sensor acknowledgement. |
| **PostgreSQL Migration Suite** | Alembic Engine | 20+ relational tables, indexes, foreign keys, constraints. | Real PostgreSQL 14+ instance. | **Alembic upgrade head & dynamic metadata inspection** on live PostgreSQL. |
| **Offline Cloud/Feed Fixtures** | Pytest fixtures | AWS posture findings, Threat Intelligence adapters. | Local offline fixtures / unconfigured state. | Verifies normalized schemas and fallback handling without external API calls or AWS charges. |

---

## 🧪 1. Backend Automated Test Suite (Pytest)

### Running Backend Tests
```powershell
.venv\Scripts\python -m pytest backend/tests -v
```

### Complete Test Catalog (24 Test Items across 15 Test Suites)

1. **`backend/tests/test_auth_and_tenancy.py`** (1 item):
   - `test_register_and_login`: User registration, bcrypt password hashing, JWT generation, and organization tenant isolation.
2. **`backend/tests/test_sensors_and_telemetry.py`** (5 items):
   - `test_sensor_lifecycle_and_telemetry`: Token issuance, SHA-256 API key hashing, heartbeat metrics, and telemetry batch ingestion.
   - `test_simulated_vs_genuine_event_classification_and_isolation`: Regression test asserting strict `is_simulated` separation, detection inheritance, incident inheritance, and dashboard breakdown.
   - `test_sensor_authentication_matrix_and_rejection_side_effects`: Tests complete 7-scenario authentication matrix (valid key, random invalid key, empty key, missing key, revoked key, expired token, cross-tenant boundary attempt); asserts HTTP 401/403 status; verifies 0 unauthorized records written to DB, 0 alerts, 0 incidents; verifies audit logging of revoked and cross-tenant attempts.
   - `test_sensor_command_security_and_replay_protection`: Verifies command isolation (Sensor B cannot see Sensor A's commands), cross-sensor acknowledgement rejection (403), unauthenticated acknowledgement rejection (401), legitimate acknowledgement (200), duplicate acknowledgement idempotency, expired command expiration & rejection (400), and command transition audit logs.
   - `test_audit_log_integrity_and_tenant_isolation`: Verifies tenant isolation on `/admin/audit-logs`, confirms zero mutation endpoints (PUT/PATCH/DELETE return 404/405), unauthenticated access blocked (401), and non-admin access blocked (403 with `AUTHZ_DENIED` audit log).
3. **`backend/tests/test_detection_and_incidents.py`** (1 item):
   - `test_detections_and_incident_workflow`: 13-rule deterministic engine, threshold evaluations, alert generation, and incident escalation.
4. **`backend/tests/test_ip_utils_and_redaction.py`** (3 items):
   - `test_ip_classification`: Dual-stack RFC classification across Public, Private, Loopback, Link-Local, and CGNAT.
   - `test_diagnostic_sanitization`: Masking of passwords, API keys, JWT tokens, AWS keys, and nested dictionaries.
   - `test_sensitive_http_headers_redaction`: Masking of Authorization, X-Sensor-Key, and Cookie HTTP headers.
5. **`backend/tests/test_ai_and_helpdesk.py`** (1 item):
   - `test_ai_helpdesk_and_fallback`: Deterministic fallback provider, 429 quota exhaustion, and Helpdesk documentation grounding.
6. **`backend/tests/test_advanced_correlation.py`** (1 item):
   - `test_advanced_correlation_and_rules`: Multi-stage attack correlation groups (`CorrelatedEventGroup`) and dynamic parameter tuning.
7. **`backend/tests/test_aws_security.py`** (1 item):
   - `test_aws_security_expansion`: AssumeRole with External ID, least-privilege IAM policy template, and offline fixture loader.
8. **`backend/tests/test_incident_timeline_and_reports.py`** (1 item):
   - `test_incident_timeline_and_multi_format_reports`: Unified chronological case timeline and multi-format CSV/JSON compliance exports.
9. **`backend/tests/test_ip_investigation.py`** (1 item):
   - `test_ip_investigation_and_grounding`: 5-tier evidence grounding, analyst dossiers, verdicts, and timeline sightings.
10. **`backend/tests/test_network_intelligence.py`** (1 item):
    - `test_network_coverage_and_topology`: Subnet/sensor coverage metrics, gateway sync adapters, and observed vs inferred topology.
11. **`backend/tests/test_release_1_regression.py`** (2 items):
    - `test_release_1_core_regression`: Core foundations regression suite verifying baseline Release 1 features remain intact.
    - `test_production_health_and_trusted_proxy_security`: Verifies database-aware `/health` status (connected, dialect, version) and strict anti-spoofing behavior of `TRUSTED_PROXIES` middleware.
12. **`backend/tests/test_release_3_capabilities.py`** (4 items):
    - `test_asset_risk_scoring_engine`: Multi-factor dynamic asset risk score calculation ($0 - 100$) and categorical tiers.
    - `test_response_playbook_approval_workflow`: Approval-based response automation, human authorization gate, sensor command queue, sensor execution acknowledgement, and safe diagnostic verification probe.
    - `test_attack_simulation_lab_and_purge`: AWS IAM escalation, credential spray correlation, and non-destructive lab purge.
    - `test_administration_and_governance`: Team member role management, integration connectors health matrix, data retention policies, and on-demand cleanup.
13. **`backend/tests/test_threat_intel_adapters.py`** (3 items):
    - `test_threat_provider_health_endpoint`: Provider operational health reporting.
    - `test_unconfigured_adapters_handle_gracefully`: Graceful degradation and transparent attribution when API keys are unset.
    - `test_normalized_threat_indicator_schema`: Standardized indicator schema normalization across AbuseIPDB, GreyNoise, AlienVault OTX, and Spamhaus.

---

## 🎭 2. Frontend End-to-End Test Suite (Playwright)

### Running Playwright Tests
```powershell
cd frontend
npx playwright test
```

### Playwright E2E Catalog (15 Browser Tests)
All 15 Playwright tests execute within headless Chromium against the Next.js production build using Playwright's network routing (`page.route`) to mock API responses and verify UI rendering, interaction flows, loading states, and error handling in isolation:

1. **Login Page:** Form submission, validation, and error alert rendering.
2. **Registration Page:** Organization enrollment, password confirmation, and loading states.
3. **Dashboard:** KPI metrics cards, Recharts 24h event timeline, and quick actions.
4. **Asset Management:** Host inventory table, hardware metrics, and filter controls.
5. **Sensor Fleet:** Enrollment token modal, copy-to-clipboard, and agent status table.
6. **IP Intelligence:** 5-tier evidence grounding tabs, analyst verdicts, and timeline.
7. **Network Intelligence:** Subnet/sensor coverage gauges, device authorization toggle, and topology view.
8. **Detection Center:** 13-rule catalog, rule toggles, and parameter tuning modal.
9. **Incident Management:** Master-detail case triage, status transitions, and timeline CSV export.
10. **AWS Cloud Security:** Zero-cost safety guarantee banner, offline fixtures loader, and IAM policy template modal.
11. **AI Security Analyst:** Scope selection, target identifier input, and 5-part advisory briefing.
12. **AI Helpdesk & RAG:** Multi-turn conversation interface, question suggestions, and documentation grounding.
13. **Reports & Exports:** Compliance summary cards and 1-click CSV/JSON download triggers.
14. **Notifications Center:** Severity-badged alerts list and mark-all-read action.
15. **Error State Handling:** API 500 failure interception and graceful alert banner verification.

---

## 💻 3. Live Integration Verification Scripts

### A. Complete Sensor-to-Incident Pipeline Verification
```powershell
.venv\Scripts\python backend/scripts/verify_sensor_pipeline.py
```
- **12 Live Steps:** Genuine Windows telemetry collection -> Operator login -> Dedicated test tenant creation (`Pipeline Verification Lab`) -> Token generation -> Enrollment handshake -> Heartbeat -> Telemetry batch ingestion -> Event persistence & simulated classification check -> Deterministic detection trigger -> Incident creation -> Dashboard segmentation -> Clean teardown with zero dev tenant pollution.
- **Negative Authentication Assertion:** Explicitly verifies that invalid sensor API keys are rejected with HTTP 401 (`Bogus API Key Rejected = True (Status Code: 401)`).

### B. Response Automation 9-Step Lifecycle Audit
```powershell
.venv\Scripts\python backend/scripts/verify_response_automation.py
```
- **9 Live Steps:** Playbook trigger -> Approval requirement enforcement (`Pending Approval`) -> Authorized operator decision (`Approved`) -> AuditLog persistence -> Sensor command dispatch -> Sensor heartbeat retrieval -> Command validation (safe probe) -> Sensor execution acknowledgement -> Final execution status & audit ledger update.
- **Dry-Run Guardrails:** Validates non-destructive `DIAGNOSTIC_PROBE` execution with zero socket manipulation; hard physical socket cut (`ISOLATE_HOST`) verified in safe dry-run mode and honestly documented as unverified for live hostile network drops.
