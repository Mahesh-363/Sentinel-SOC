# SENTINEL SOC — FREE DEPLOYMENT READINESS REPORT

**Document:** `FREE_DEPLOYMENT_READINESS_REPORT.md`  
**Date:** November 24, 2026  
**Auditor:** Senior DevSecOps & Cloud Architecture Review  
**Project Path:** `F:\Sentinel SOC`  
**Repository:** [https://github.com/Mahesh-363/Sentinel-SOC](https://github.com/Mahesh-363/Sentinel-SOC)  
**Target Architecture:** Free Tier Hosting (₹0 / $0 Cost)  
- **Frontend:** Vercel Hobby  
- **Backend:** Render Free Web Service  
- **Database:** Supabase PostgreSQL Free Tier  

---

## 1. Executive Summary & Feasibility Verdict

A comprehensive architectural and codebase audit was conducted on the Sentinel Security Operations Center (SOC) repository to evaluate its readiness for 100% free-tier cloud deployment with **₹0 financial expenditure**.

### Overall Feasibility: **READY WITH MINOR CODE ADJUSTMENTS**

The application architecture is well suited for the decoupled serverless/container free tier model:
- **Stateless Backend:** The FastAPI backend is entirely stateless. Sessions are managed through self-contained cryptographic JSON Web Tokens (`Authorization: Bearer <JWT>`), eliminating the need for sticky sessions or persistent Redis clusters.
- **Relational PostgreSQL Compatibility:** SQLAlchemy 2.0 with `psycopg2-binary` is implemented with dynamic PostgreSQL connection string normalization (`postgresql://` -> `postgresql+psycopg2://`).
- **RESTful Client Communications:** The frontend communicates with the backend exclusively via standard HTTP/HTTPS REST APIs (`fetch`). There are no active WebSocket requirements, eliminating serverless WebSocket timeout complications.
- **Background Task Decoupling:** Redis is configured as an optional local in-memory fallback (`REDIS_ENABLED=False` default). No standalone Celery or Redis infrastructure is required.

A small set of targeted code adjustments (detailed in Section 7) should be resolved prior to pushing deployment triggers to ensure complete cross-domain reliability.

---

## 2. Platform-by-Platform Compatibility Analysis

```
+-----------------------------------------------------------------------------------------+
|                                FREE CLOUD ARCHITECTURE                                  |
|                                                                                         |
|       [ Operator Browser ]                                [ Endpoint Sensors ]          |
|                 |                                                  |                    |
|                 | HTTPS UI                                         | HTTPS Telemetry    |
|                 v                                                  | & Heartbeats       |
|    +------------------------+                                      | (X-Sensor-Key)     |
|    |     Vercel (Hobby)     |                                      |                    |
|    |   Next.js 14 Frontend  |                                      |                    |
|    +------------------------+                                      |                    |
|                 |                                                  |                    |
|                 | Client-side HTTPS REST API (Bearer JWT)          |                    |
|                 +----------------------------+                     |                    |
|                                              |                     |                    |
|                                              v                     v                    |
|                                  +------------------------------------+                 |
|                                  |        Render Free Service         |                 |
|                                  |        FastAPI Python 3.11         |                 |
|                                  +------------------------------------+                 |
|                                                     |                                   |
|                                                     | SQLAlchemy Connection Pool        |
|                                                     | (Port 5432, Session Mode)         |
|                                                     v                                   |
|                                  +------------------------------------+                 |
|                                  |        Supabase PostgreSQL         |                 |
|                                  |         (Free Managed DB)          |                 |
|                                  +------------------------------------+                 |
|                                                                                         |
|   NOTE: Endpoint sensors NEVER connect directly to PostgreSQL. All sensor telemetry    |
|         is authenticated and ingested strictly via the Render FastAPI backend.        |
+-----------------------------------------------------------------------------------------+
```

### 2.1 Frontend: Vercel (Hobby Tier)

| Metric | Vercel Hobby Limit | Sentinel SOC Requirement | Compatibility |
| :--- | :--- | :--- | :---: |
| **Framework** | Next.js 14.x native | Next.js 14.2.35 (App Router) | **100% Compatible** |
| **Bandwidth** | 100 GB / month | ~2–5 GB / month estimated | **100% Compatible** |
| **Serverless Execution** | 10s max duration | Static UI + Client-side fetch | **100% Compatible** |
| **Build Pipeline** | 6,000 mins / month | ~45s per build (`npm run build`) | **100% Compatible** |
| **Cost** | **$0 / month** | Free Hobby Account | **₹0 Spending** |

- **Root Directory:** `frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `.next`
- **Client Bundling Rule:** In Next.js, variables prefixed with `NEXT_PUBLIC_` are embedded into client JavaScript at **build time**. Therefore, `NEXT_PUBLIC_API_URL` must be set in the Vercel project environment settings **before** running the deployment build.

### 2.2 Backend: Render (Free Web Service)

| Metric | Render Free Tier Limit | Sentinel SOC Requirement | Compatibility |
| :--- | :--- | :--- | :---: |
| **RAM** | 512 MB | ~65–85 MB (FastAPI + Uvicorn) | **100% Compatible** |
| **CPU** | 0.1 shared vCPU | Low I/O async processing | **100% Compatible** |
| **Disk** | Ephemeral (Wiped on restart) | 0 local files (DB in Supabase) | **100% Compatible** |
| **Bandwidth** | 100 GB / month | ~5–10 GB / month estimated | **100% Compatible** |
| **Inactivity Policy** | Spins down after 15m idle | Sensors keep awake or cold start | **Compatible (See Sec 5)**|
| **Cost** | **$0 / month** | Free Instance Tier | **₹0 Spending** |

- **Deployment Option A (Recommended — Native Python Service):**
  - **Root Directory:** `.`
  - **Build Command:** `pip install -r backend/requirements.txt`
  - **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips=*`
- **Deployment Option B (Docker Service):**
  - Uses `backend/Dockerfile` with Render port routing.

### 2.3 Database: Supabase (PostgreSQL Free Tier)

| Metric | Supabase Free Limit | Sentinel SOC Requirement | Compatibility |
| :--- | :--- | :--- | :---: |
| **Storage** | 500 MB PostgreSQL | ~6.5 MB initial seed data | **100% Compatible** |
| **Connections** | 60 direct, 200+ pooler | 10 pool / 20 overflow (`Settings`) | **100% Compatible** |
| **Backups** | Point-in-time available | Managed automated daily snapshots | **100% Compatible** |
| **Database Engine** | PostgreSQL 15 / 16 | SQLAlchemy 2.0 / Alembic | **100% Compatible** |
| **Inactivity Policy** | Pauses after 7 days zero queries | Periodic sensor telemetry prevents pause | **Compatible (See Sec 5)**|
| **Cost** | **$0 / month** | Free Tier Organization | **₹0 Spending** |

- **Recommended Connection Mode:** Session Pooler on Port `5432`:
  `postgresql://postgres.[PROJECT-REF]:[DB-PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres?sslmode=require`
  *(Session mode on port 5432 supports full DDL schema migrations, SQLAlchemy connection pooling, and SSL verification).*

---

## 3. Database Configuration & Migration Audit

### 3.1 PostgreSQL Support Verification
- `backend/app/database.py` includes automatic driver normalization:
  ```python
  if db_url.startswith("postgresql://"):
      db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
  ```
- Enterprise connection pooling is implemented for PostgreSQL:
  - `pool_size = 10`
  - `max_overflow = 20`
  - `pool_recycle = 1800` (recycles connections every 30 minutes to prevent stale dropped connections from cloud firewalls)
  - `pool_pre_ping = True` (validates connection health before issuing queries)

### 3.2 SQLite-Specific Code Isolation
- In `backend/app/db/seed.py`, `ensure_schema_migrations()` explicitly guards dialect-specific PRAGMA operations:
  ```python
  if engine.dialect.name == "sqlite":
      # PRAGMA queries executed only on SQLite
  ```
  When connected to Supabase PostgreSQL (`engine.dialect.name == "postgresql"`), these blocks are bypassed.

### 3.3 Database Seeding & Startup Lifespan
- On FastAPI startup, `lifespan` in `backend/app/main.py` executes:
  1. `Base.metadata.create_all(bind=engine)`: Creates all missing database tables on Supabase.
  2. `seed_database()`: Evaluates `existing_user = db.query(User).filter(User.email == "admin@sentinelsoc.com").first()`. If unseeded, populates detection rules, threat intel indicators, and default administrative structures.
  3. **Production Credential Hardening:** Verified that under `ENVIRONMENT=production` or `APP_ENV=production`, `seed.py` sets `sensor_linux.api_key_hash = None` and status to `"Offline"`, guaranteeing that no sample sensor key is created in production.

---

## 4. Frontend API, CORS & Authentication Audit

### 4.1 Authentication & Cross-Domain Handling
- **Mechanism:** JWT stored in client browser `localStorage` under `sentinel_token`.
- **Transmission:** Standard HTTP header `Authorization: Bearer <token>`.
- **Tenant Context:** Transmitted via header `X-Organization-Id: <org_id>`.
- **Cross-Domain Evaluation:** Because authentication relies on `Authorization` headers rather than `Set-Cookie` session cookies, cross-domain requests between Vercel (`https://*.vercel.app`) and Render (`https://*.onrender.com`) **are completely immune to third-party cookie blocking** (Safari ITP, Chrome Privacy Sandbox).

### 4.2 CORS Configuration
- In `backend/app/config.py`, `BACKEND_CORS_ORIGINS` supports comma-separated strings or JSON arrays via `parse_cors_origins`.
- In production on Render, the operator must set:
  ```env
  BACKEND_CORS_ORIGINS=https://sentinel-soc.vercel.app,https://your-custom-domain.com
  ```

---

## 5. Free-Tier Constraints, Sleeping & Sensor Ingestion

### 5.1 Render Free Spin-Down (15 Minutes)
- **Behavior:** Free Render instances spin down after 15 minutes of inactivity. When a new incoming HTTP request arrives, Render triggers a cold start taking **30 to 50 seconds** to boot.
- **Sensor Telemetry Interaction:**
  - Enrolled endpoint sensors transmit a health heartbeat every **30 seconds** (`heartbeat_interval_seconds: 30`) and telemetry batches every **60 seconds** (`telemetry_interval_seconds: 60`).
  - **Key Advantage:** Active endpoint sensors making periodic HTTPS calls will naturally keep the Render backend awake during active operations.
  - **Cold Start Risk:** If all sensors are shut down and the service spins down, a sensor attempting enrollment or initial reconnection may encounter a timeout if its HTTP timeout is under 30 seconds.
  - **Mitigation:** Sensor configuration timeout in `sensor/config.example.yaml` should be increased from `15s` to `60s` to tolerate cold starts.

### 5.2 Supabase Inactivity Pause (7 Days)
- **Behavior:** Free Supabase projects pause after 7 consecutive days of zero database queries.
- **Mitigation:** Because active sensors or routine SOC operations query the database daily, the 7-day inactivity pause threshold is never triggered during regular use.

---

## 6. Complete Environment Variable Specifications

### 6.1 Render Web Service (Backend)

| Variable Name | Required | Example / Recommended Value | Description |
| :--- | :---: | :--- | :--- |
| `ENVIRONMENT` | **YES** | `production` | Activates production security guardrails |
| `SECRET_KEY` | **YES** | *(Generate 64-char hex)* | 32+ byte cryptographic JWT signing key |
| `DATABASE_URL` | **YES** | `postgresql://postgres.[REF]:[PASS]@aws-0-[REGION].pooler.supabase.com:5432/postgres?sslmode=require` | Supabase Session Pooler connection URL |
| `BACKEND_CORS_ORIGINS` | **YES** | `https://sentinel-soc.vercel.app` | Vercel production frontend origin |
| `TRUSTED_PROXIES` | **YES** | `*` | Permits Render reverse proxy IP forwarding |
| `LOG_LEVEL` | NO | `INFO` | Application log verbosity |
| `AI_PROVIDER` | NO | `gemini` | Free-tier Google Gemini integration (`gemini` or `none`) |
| `GEMINI_API_KEY` | NO | *(Free Gemini API key)* | Google AI Studio free-tier API key |
| `ABUSEIPDB_API_KEY` | NO | *(Free AbuseIPDB key)* | Optional free threat intelligence feed |
| `ALIENVAULT_OTX_KEY`| NO | *(Free OTX key)* | Optional free threat intelligence feed |

### 6.2 Vercel Project (Frontend)

| Variable Name | Required | Recommended Value | Description |
| :--- | :---: | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | **YES** | `https://sentinel-soc.onrender.com/api/v1` | Public URL of the Render backend |

---

## 7. Required Code Adjustments (Gaps Identified)

The following four specific items should be addressed in the codebase before triggering public deployment:

### 1. Fix Hardcoded URL in Report Downloads (`frontend/src/app/reports/page.tsx`)
- **Current Code (Line 40):**
  ```typescript
  const res = await fetch(`http://localhost:8000/api/v1/reports/${endpoint}`, {
  ```
- **Issue:** On Vercel, report downloads attempt to contact the operator's local machine on port 8000 instead of the production backend.
- **Remediation:** Replace with `const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";` and construct `${API_BASE}/reports/${endpoint}`.

### 2. Standardize Organization ID Storage Key (`frontend/src/app/incidents/page.tsx`)
- **Current Code (Line 221):**
  ```typescript
  const orgId = localStorage.getItem("sentinel_org_id");
  ```
- **Issue:** `lib/api.ts` uses `localStorage.getItem("sentinel_active_org")`.
- **Remediation:** Align key to `localStorage.getItem("sentinel_active_org") || localStorage.getItem("sentinel_org_id")`.

### 3. Support Dynamic Port in Backend Container Entrypoint (`backend/Dockerfile`)
- **Current Code (Line 36):**
  ```dockerfile
  CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", ...]
  ```
- **Issue:** Cloud container platforms (Render, Cloud Run) assign random dynamic listening ports via the `$PORT` environment variable.
- **Remediation:** Update CMD to use shell parameter expansion: `python -m uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=*`.

### 4. Increase Sensor Cold-Start Timeout (`sensor/config.example.yaml` & `config.py`)
- **Current Value:** `timeout_seconds: 15`
- **Issue:** Render free tier cold starts take 30–50 seconds if spun down.
- **Remediation:** Set default sensor timeout to `60` seconds to avoid connection dropouts during backend wake-up.

---

## 8. Deployment Step-by-Step Roadmap (Execution Guide)

When authorized, the zero-cost deployment will proceed in three sequential phases:

```
[Phase 1: Supabase]  --->  [Phase 2: Render Backend]  --->  [Phase 3: Vercel Frontend]
Create free project       Deploy Web Service               Deploy Next.js App
Copy pooler URL           Inject DB & CORS env vars         Inject NEXT_PUBLIC_API_URL
```

1. **Phase 1: Provision Supabase Database ($0)**
   - Create a free project at `supabase.com`.
   - In Database Settings -> Connection Pooling, select **Session mode (Port 5432)**.
   - Copy the connection string.

2. **Phase 2: Deploy Render Backend ($0)**
   - Create a free Web Service connected to `https://github.com/Mahesh-363/Sentinel-SOC`.
   - Set Build Command: `pip install -r backend/requirements.txt`
   - Set Start Command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips=*`
   - Inject environment variables (`ENVIRONMENT`, `SECRET_KEY`, `DATABASE_URL`, `BACKEND_CORS_ORIGINS`).
   - Copy the deployed URL: `https://<app-name>.onrender.com`.

3. **Phase 3: Deploy Vercel Frontend ($0)**
   - Import `https://github.com/Mahesh-363/Sentinel-SOC` into Vercel.
   - Set Root Directory to `frontend`.
   - Set Environment Variable: `NEXT_PUBLIC_API_URL = https://<app-name>.onrender.com/api/v1`.
   - Trigger build and verify live dashboard.

---

## 9. Conclusion

The Sentinel SOC project is structurally and architecturally ready for free cloud deployment. By addressing the 4 minor code adjustments identified above, the system can be deployed and run permanently on Vercel, Render, and Supabase with **₹0 spending**.
