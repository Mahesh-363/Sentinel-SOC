# SENTINEL SOC — Installation & Setup Guide

Welcome to the comprehensive installation guide for **SENTINEL SOC**. This document covers prerequisites, environment configuration, database setup (SQLite and PostgreSQL), local native development, Docker Compose deployment, endpoint sensor installation, and post-installation validation.

---

## 📋 Table of Contents
1. [System Requirements](#1-system-requirements)
2. [Prerequisites](#2-prerequisites)
3. [Repository Setup & Configuration](#3-repository-setup--configuration)
4. [Deployment Option A: Local Native Setup (Zero-Cost / Lab)](#4-deployment-option-a-local-native-setup-zero-cost--lab)
5. [Deployment Option B: Production Setup with PostgreSQL & Alembic](#5-deployment-option-b-production-setup-with-postgresql--alembic)
6. [Deployment Option C: Docker Compose Deployment](#6-deployment-option-c-docker-compose-deployment)
7. [Endpoint Sensor Agent Installation](#7-endpoint-sensor-agent-installation)
8. [Post-Installation Validation & Testing](#8-post-installation-validation--testing)
9. [Troubleshooting & FAQ](#9-troubleshooting--faq)

---

## 1. System Requirements

| Component | Minimum Specification | Recommended Specification |
| :--- | :--- | :--- |
| **Operating System** | Windows 10/11, Ubuntu 20.04+, Debian 11+, RHEL 8+, macOS 12+ | Windows Server 2022 / Ubuntu 22.04 LTS |
| **CPU** | 2 cores (x86_64 or ARM64) | 4+ cores |
| **Memory (RAM)** | 4 GB | 8 GB+ |
| **Disk Space** | 2 GB free space | 10 GB+ SSD |
| **Network** | Outbound HTTPS for Threat Feeds | Static IP / Domain for SOC Web UI |

---

## 2. Prerequisites

Ensure the following runtimes are installed on your system before proceeding:

### A. Python 3.11+
- Verify with: `python --version` or `python3 --version`
- Ensure `pip` and `venv` are available.

### B. Node.js 18+ (Node 20 LTS Recommended)
- Verify with: `node --version` and `npm --version`

### C. (Optional) PostgreSQL 14+
- Required only if running production relational storage instead of the built-in SQLite engine.
- Verify with: `psql --version`

### D. (Optional) Docker & Docker Compose
- Required only for containerized deployment.
- Verify with: `docker --version` and `docker compose version`

---

## 3. Repository Setup & Configuration

### 3.1 Clone the Repository
```bash
git clone https://github.com/your-org/sentinel-soc.git
cd sentinel-soc
```

### 3.2 Configure Environment Variables
Copy the provided `.env.example` file to create your active `.env`:

```bash
# On Linux / macOS:
cp .env.example .env

# On Windows (PowerShell):
Copy-Item .env.example .env
```

### 3.3 Critical Configuration Variables
Edit `.env` and configure key parameters:

```ini
# Application Environment
ENVIRONMENT=production          # "development", "staging", or "production"
SECRET_KEY=change-this-to-a-cryptographically-random-64-character-hex-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# Database Configuration
# Default Lab / Zero-Setup (SQLite):
DATABASE_URL=sqlite:///./sentinel.db

# Production Relational Database (PostgreSQL):
# DATABASE_URL=postgresql+psycopg2://sentinel_user:your_password@localhost:5432/sentinel_prod

# Database Connection Pool Settings (PostgreSQL only)
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=1800
DB_POOL_PRE_PING=true

# Security & Reverse Proxy Settings
BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
TRUSTED_PROXIES=127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16

# Application Logging
LOG_LEVEL=INFO
LOG_FILE=logs/sentinel.log

# Threat Intelligence (Optional - Free-Tier Community APIs)
ABUSEIPDB_API_KEY=
GREYNOISE_API_KEY=
ALIENVAULT_OTX_KEY=
SPAMHAUS_DQS_KEY=

# Advisory AI Services (Optional - Privacy-Preserving)
GEMINI_API_KEY=
LOCAL_AI_BASE_URL=http://localhost:11434/v1
```

> [!IMPORTANT]
> Always generate a secure `SECRET_KEY` in production environments:
> `python -c "import secrets; print(secrets.token_hex(32))"`

---

## 4. Deployment Option A: Local Native Setup (Zero-Cost / Lab)

This mode runs directly on your workstation or server using SQLite and requires zero external database installation.

### 4.1 Backend Setup (FastAPI)
1. **Create and activate a Python virtual environment:**
   ```bash
   # Windows (PowerShell):
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / macOS:
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install backend dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r backend/requirements.txt
   ```

3. **Initialize the database with default seed data:**
   ```bash
   python -m backend.app.db.seed
   ```
   *Default Admin Credentials:*
   - **Email:** `admin@sentinelsoc.com`
   - **Password:** `SentinelAdmin123!`
   - **Organization:** Global Defense SOC

   *(If you ever need to reset the administrator password, run: `python scripts/reset_admin_password.py`)*

4. **Launch the backend server:**
   ```bash
   python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   - API Root: `http://127.0.0.1:8000`
   - Interactive Swagger API Docs: `http://127.0.0.1:8000/docs`
   - Healthcheck Endpoint: `http://127.0.0.1:8000/health`

### 4.2 Frontend Setup (Next.js 14)
1. **Open a new terminal and navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install Node.js dependencies:**
   ```bash
   npm install
   ```

3. **Launch the frontend development server:**
   ```bash
   npm run dev
   ```
   - Web Console: `http://localhost:3000`

4. *(Alternative)* **Build and run production frontend:**
   ```bash
   npm run build
   npm start
   ```

---

## 5. Deployment Option B: Production Setup with PostgreSQL & Alembic

For production deployments requiring high concurrency, connection pooling, and multi-worker scalability, PostgreSQL is recommended.

### 5.1 Create PostgreSQL Database & User
Connect to your PostgreSQL cluster using `psql`:

```sql
CREATE DATABASE sentinel_prod;
CREATE USER sentinel_user WITH ENCRYPTED PASSWORD 'ComplexPassword123!';
GRANT ALL PRIVILEGES ON DATABASE sentinel_prod TO sentinel_user;
ALTER DATABASE sentinel_prod OWNER TO sentinel_user;
```

### 5.2 Configure `DATABASE_URL` in `.env`
Update `.env` to point to PostgreSQL:
```ini
DATABASE_URL=postgresql+psycopg2://sentinel_user:ComplexPassword123!@localhost:5432/sentinel_prod
```

### 5.3 Run Alembic Schema Migrations
Execute Alembic migrations to create all database tables and indexes:

```bash
# Ensure virtualenv is active
alembic upgrade head
```

Verify migration status:
```bash
alembic current
```

### 5.4 Seed Initial Production Data
Seed the default administrator user, organization, and 13 pre-tuned detection rules:

```bash
python -m backend.app.db.seed
```

### 5.5 Production Process Management
Run the FastAPI backend with multiple Uvicorn workers behind a process supervisor (`systemd` or `supervisord`):

```bash
python -m uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --proxy-headers \
  --forwarded-allow-ips="*"
```

---

## 6. Deployment Option C: Docker Compose Deployment

The quickest path to a fully containerized deployment with automated healthchecks and dependency management.

### 6.1 Build and Start Containers
```bash
docker compose up -d --build
```

### 6.2 Monitor Health & Logs
```bash
# Check container status
docker compose ps

# View backend logs
docker compose logs -f backend

# View frontend logs
docker compose logs -f frontend
```

### 6.3 Service Ports
- **Frontend SOC UI:** `http://localhost:3000`
- **Backend API:** `http://localhost:8000`
- **Healthcheck:** `http://localhost:8000/health`
- **PostgreSQL Database:** `localhost:5432` (internal Docker network: `postgres:5432`)

---

## 7. Endpoint Sensor Agent Installation

The Sentinel Endpoint Sensor monitors host CPU, memory, disk, network sockets, active processes, and ARP neighbor tables.

### 7.1 Generate Sensor Enrollment Token
1. Log in to the Sentinel SOC dashboard (`http://localhost:3000`).
2. Navigate to **Sensors** (`/sensors`).
3. Click **Enroll New Sensor** and select your target platform (**Windows** or **Linux**).
4. Copy the generated single-use cryptographic enrollment token.

### 7.2 Windows Sensor Deployment

#### Quick Run:
```powershell
python sensors/windows/sentinel_sensor.py \
  --server http://localhost:8000 \
  --enrollment-token YOUR_ENROLLMENT_TOKEN
```

#### Production Windows Service (via NSSM):
```powershell
# Download NSSM (Non-Sucking Service Manager)
nssm install SentinelSensor "C:\sentinel-soc\.venv\Scripts\python.exe" "C:\sentinel-soc\sensors\windows\sentinel_sensor.py --server https://soc.yourcompany.com"
nssm set SentinelSensor AppDirectory "C:\sentinel-soc"
nssm set SentinelSensor Start SERVICE_AUTO_START
nssm start SentinelSensor
```

### 7.3 Linux Sensor Deployment

#### Quick Run:
```bash
python3 sensors/linux/sentinel_sensor.py \
  --server http://localhost:8000 \
  --enrollment-token YOUR_ENROLLMENT_TOKEN
```

#### Production Systemd Service:
Create `/etc/systemd/system/sentinel-sensor.service`:

```ini
[Unit]
Description=Sentinel SOC Endpoint Sensor Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/sentinel-soc
ExecStart=/opt/sentinel-soc/.venv/bin/python3 /opt/sentinel-soc/sensors/linux/sentinel_sensor.py --server https://soc.yourcompany.com
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sentinel-sensor
sudo systemctl start sentinel-sensor
```

---

## 8. Post-Installation Validation & Testing

Verify that your deployment is working end-to-end:

### 8.1 Backend Healthcheck
```bash
curl -i http://localhost:8000/health
```
Expected output:
```json
{
  "status": "healthy",
  "app": "Sentinel SOC",
  "version": "1.0.0",
  "environment": "production",
  "database": {
    "status": "connected",
    "dialect": "postgresql",
    "error": null
  }
}
```

### 8.2 Run Backend Unit & Integration Tests (25 Tests)
```bash
python -m pytest backend/tests
```
All 25 tests should pass with 100% green status.

### 8.3 Run Sensor Pipeline Verification
```bash
python backend/scripts/verify_sensor_pipeline.py
```
Validates the full 12-step pipeline: genuine Windows telemetry ingestion, token enrollment, 401 bogus key rejection, deterministic detection rule execution, incident generation, and isolated tenant cleanup.

### 8.4 Run Playwright Frontend E2E Tests (15 Tests)
```bash
cd frontend
npx playwright test
```
Validates all 15 core UI user workflows and pages.

---

## 9. Troubleshooting & FAQ

### Q1: The backend reports `ModuleNotFoundError: No module named 'psycopg'`
**Solution:** Ensure `psycopg2-binary` is installed: `pip install psycopg2-binary`. The application automatically uses the `postgresql+psycopg2://` driver scheme.

### Q2: Healthcheck returns HTTP 503 `status: degraded`
**Solution:** Check `database.error` in the response. Verify that your PostgreSQL database service is running, that credentials in `DATABASE_URL` are valid, and that the database port (`5432`) is reachable.

### Q3: Client IP addresses appear as `127.0.0.1` behind reverse proxy
**Solution:** Configure your reverse proxy IP or CIDR range in `TRUSTED_PROXIES` in `.env`. For example: `TRUSTED_PROXIES=127.0.0.1,10.0.0.0/8,172.16.0.0/12`.

### Q4: CORS error when accessing API from frontend
**Solution:** Ensure the frontend origin is included in `BACKEND_CORS_ORIGINS` in `.env`. Comma-separated strings and JSON array formats are both supported.

### Q5: Sensor enrollment fails with HTTP 400 or 401
**Solution:** Enrollment tokens are single-use and expire after 48 hours. Generate a fresh enrollment token from `/sensors` in the web UI.
