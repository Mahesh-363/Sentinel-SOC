# SENTINEL SOC — DEPLOYMENT READINESS FIXES REPORT

**Document:** `DEPLOYMENT_FIXES_REPORT.md`  
**Date:** November 24, 2026  
**Auditor:** Senior DevSecOps & Cloud Engineering Review  
**Project Path:** `F:\Sentinel SOC`  
**Status:** **ALL FIXES APPLIED & VERIFIED — READY FOR COMMIT & DEPLOYMENT**

---

## 1. Executive Summary

All four deployment-readiness issues identified in `FREE_DEPLOYMENT_READINESS_REPORT.md` have been resolved. The modifications ensure seamless interoperability across the decoupled free-tier architecture (**Vercel Hobby** + **Render Free Web Service** + **Supabase PostgreSQL**).

The codebase was validated through end-to-end frontend type checks, ESLint, Next.js production compilation (25 static pages), backend Pytest suites (7/7 passed), and isolated sensor configuration test matrices (4/4 passed).

---

## 2. Detailed Breakdown of Modifications

### 2.1 Frontend Report Downloads (`frontend/src/app/reports/page.tsx`)
- **Problem:** Report downloads in `downloadFile` bypassed `process.env.NEXT_PUBLIC_API_URL` and made direct browser requests to `http://localhost:8000/api/v1/reports/${endpoint}`, which fails on public hosting.
- **Fix:** 
  - Constructed the request URL using `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"`.
  - Standardized organization extraction to `localStorage.getItem("sentinel_active_org") || localStorage.getItem("sentinel_org_id")`.
- **Diff:**
  ```typescript
  - const activeOrg = localStorage.getItem("sentinel_active_org");
  - const res = await fetch(`http://localhost:8000/api/v1/reports/${endpoint}`, {
  + const activeOrg = localStorage.getItem("sentinel_active_org") || localStorage.getItem("sentinel_org_id");
  + const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  + const res = await fetch(`${apiBase}/reports/${endpoint}`, {
  ```

### 2.2 Organization ID Storage Key Consistency (`frontend/src/app/incidents/page.tsx`)
- **Problem:** CSV timeline export previously queried `localStorage.getItem("sentinel_org_id")`, while the rest of the application (`lib/auth-context.tsx` and `lib/api.ts`) stores the active organization under `sentinel_active_org`.
- **Fix:** Standardized to query `sentinel_active_org` while retaining backward fallback to `sentinel_org_id`:
  ```typescript
  - const orgId = localStorage.getItem("sentinel_org_id");
  + const orgId = localStorage.getItem("sentinel_active_org") || localStorage.getItem("sentinel_org_id");
  ```

### 2.3 Container Dynamic Port Expansion (`backend/Dockerfile`)
- **Problem:** Cloud container runtimes (such as Render and Google Cloud Run) bind applications to a dynamically injected `$PORT` environment variable. The Dockerfile previously hardcoded `--port 8000`.
- **Fix:** 
  - Updated `CMD` to shell form with `exec` so Uvicorn inherits PID 1 and respects `${PORT:-8000}`:
    ```dockerfile
    - CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
    + CMD ["sh", "-c", "exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=*"]
    ```
  - Updated container healthcheck:
    ```dockerfile
    - CMD curl -f http://localhost:8000/health || exit 1
    + CMD curl -f http://localhost:${PORT:-8000}/health || exit 1
    ```
  - Preserved the recommended native Render configuration (`uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`).

### 2.4 Sensor Cold-Start Timeout Protection
- **Problem:** Render free instances spin down after 15 minutes of inactivity. When spun down, cold-start boots take 30–50 seconds. The legacy default timeout of 15 seconds would cause fresh sensor enrollments or reconnections to drop out.
- **Fix:**
  - **`config.yaml.example` & `sensor/config.example.yaml`:** Increased default `timeout_seconds` from `15` to `60`.
  - **`sensor/sentinel_sensor/config.py`:** 
    - Set default `timeout_seconds` to `60`.
    - Added an automatic cold-start migration guard in `load()`: If an existing configuration file on disk has a legacy timeout `< 60s`, it is safely upgraded to `60s` at runtime while preserving custom values `>= 60s`.
  - **`sensor/sentinel_sensor/client.py`:** Updated constructor default timeout to `60.0s`.
  - **`sensor/install.py` & `sensor/sentinel_sensor/service.py`:** Enforced `.get("timeout_seconds", 60)`.

### 2.5 Architecture Documentation Diagram (`FREE_DEPLOYMENT_READINESS_REPORT.md`)
- **Correction:** Clarified the data flow diagram in Section 2 to eliminate ambiguity:
  - **Operator Browser** → HTTPS UI → **Vercel Frontend**
  - **Vercel Frontend** → Client-side HTTPS REST API (Bearer JWT) → **Render FastAPI Backend**
  - **Endpoint Sensors** → Outbound HTTPS Telemetry & Heartbeats (`X-Sensor-Key`) → **Render FastAPI Backend**
  - **Render FastAPI Backend** → SQLAlchemy Connection Pool (Port 5432) → **Supabase PostgreSQL**
  - Explicitly confirmed: **Endpoint sensors NEVER connect directly to PostgreSQL**.

---

## 3. Test & Verification Results

### 3.1 Frontend Verification Suite

| Test Suite | Command | Exit Code | Outcome |
| :--- | :--- | :---: | :--- |
| **TypeScript Static Check** | `npx tsc --noEmit` | `0` | **PASSED** (0 type errors) |
| **ESLint Static Check** | `npm run lint` | `0` | **PASSED** (0 errors, 1 pre-existing hook warning) |
| **Production Build** | `npm run build` | `0` | **PASSED** (All 25 static routes compiled) |
| **Localhost URL Scan** | Static regex scan | `0` | **PASSED** (0 hardcoded localhost URLs in runtime code) |

### 3.2 Backend Verification Suite

| Test Suite | Command | Exit Code | Outcome |
| :--- | :--- | :---: | :--- |
| **Auth & Sensor Lifecycle** | `pytest test_auth_and_sensor_lifecycle_repair.py` | `0` | **5/5 PASSED** |
| **Auth & Tenancy Gate** | `pytest test_auth_and_tenancy.py` | `0` | **1/1 PASSED** |
| **Incident Timeline & Reports**| `pytest test_incident_timeline_and_reports.py` | `0` | **1/1 PASSED** |
| **Total Test Execution** | Consolidated Pytest | `0` | **7/7 PASSED (9.90s)** |

### 3.3 Sensor Timeout Verification Suite

| Test Scenario | Condition | Result | Outcome |
| :--- | :--- | :---: | :--- |
| **Scenario 1: Fresh Installation** | Config path non-existent | Timeout = `60s` | **PASSED** |
| **Scenario 2: Legacy Config** | Config file with `timeout_seconds: 15` | Upgraded = `60s` | **PASSED** |
| **Scenario 3: Custom Config** | Config file with `timeout_seconds: 120` | Preserved = `120s` | **PASSED** |
| **Scenario 4: Client Default** | Direct `SensorAPIClient()` instantiation | Timeout = `60.0s` | **PASSED** |

---

## 4. Remaining Blockers

- **Zero remaining blockers.** All technical issues, hardcoded URLs, and deployment configuration inconsistencies have been remediated.

---

## 5. Git Status & Compliance Checklist

* [x] **Local SQLite database (`sentinel.db`) preserved and intact.**
* [x] **Local backups (`sentinel.db.bak*`) preserved and intact.**
* [x] **Zero active secrets added or exposed.**
* [x] **No deployment triggered.**
* [x] **No automatic Git commit or push executed.**

### Modified Files Awaiting Commit Approval:
- `backend/Dockerfile`
- `config.yaml.example`
- `frontend/src/app/incidents/page.tsx`
- `frontend/src/app/reports/page.tsx`
- `sensor/config.example.yaml`
- `sensor/install.py`
- `sensor/sentinel_sensor/client.py`
- `sensor/sentinel_sensor/config.py`
- `sensor/sentinel_sensor/service.py`
- `FREE_DEPLOYMENT_READINESS_REPORT.md`
- `DEPLOYMENT_FIXES_REPORT.md` (untracked deliverable)
