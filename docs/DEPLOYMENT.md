# SENTINEL SOC — Production & Deployment Architecture Guide

**Last Updated:** November 17, 2026 (Phase 4 Final Production Hardening)

---

## 1. Architecture Overview & Deployment Topologies

Sentinel SOC supports three distinct deployment topologies depending on operational requirements:

1. **Native Workstation / Lab Mode:** Local Python virtual environment and Node.js process using zero-config SQLite persistence (`sentinel.db`) and in-memory caches. Ideal for development, testing, and isolated cybersecurity training.
2. **Production Containerized Stack (Docker Compose):** Managed multi-container composition orchestrating PostgreSQL 16, Redis 7, Sentinel Core Backend, and Next.js Frontend with automated container healthchecks and dependency management.
3. **Enterprise Bare-Metal / VM Cluster:** High-availability deployment utilizing dedicated PostgreSQL clusters, Redis instances, multiple Uvicorn workers behind a systemd process supervisor, and an NGINX or Traefik reverse proxy terminating TLS.

---

## 2. PostgreSQL Configuration & Alembic Migrations

Sentinel SOC utilizes SQLAlchemy 2.0 with the `psycopg2-binary` driver. The platform automatically normalizes legacy `postgresql://` URIs to `postgresql+psycopg2://` at runtime.

### 2.1 Database Connection Pooling Settings
In production, database connections are managed via SQLAlchemy QueuePool configured via `.env`:

```ini
# PostgreSQL Connection URL
DATABASE_URL=postgresql+psycopg2://sentinel_user:your_secure_password@localhost:5432/sentinel_prod

# Connection Pool Tuning
DB_POOL_SIZE=10              # Base persistent connection pool size
DB_MAX_OVERFLOW=20           # Maximum burst connections beyond pool size
DB_POOL_RECYCLE=1800         # Recycle connections after 30 minutes to prevent stale TCP drops
DB_POOL_PRE_PING=true        # Issue a 'SELECT 1' test ping prior to checkout
```

### 2.2 Alembic Migration Workflow
Database schema definitions are version-controlled using Alembic migrations in the `alembic/` directory.

To apply migrations on a new or existing database:
```bash
# Upgrade database schema to latest revision
alembic upgrade head

# Inspect current revision status
alembic current

# Check migration history
alembic history --verbose
```

To seed initial organizational tenants, administrative credentials, and the 13 default detection rules:
```bash
python -m backend.app.db.seed
```

> [!NOTE]
> `backend/app/db/seed.py` includes dialect-aware checks. SQLite PRAGMA table inspections are strictly executed only when running on SQLite, preventing aborted transaction warnings on PostgreSQL.

---

## 3. Docker Compose Production Deployment

The root `docker-compose.yml` provides a turnkey production stack.

### 3.1 Docker Compose Services
- **`postgres`:** PostgreSQL 16 Alpine container with persistent named volume `postgres_data` and healthcheck (`pg_isready`).
- **`redis`:** Redis 7 Alpine container for threat intelligence caching.
- **`backend`:** FastAPI application running Uvicorn with `--proxy-headers` and `--forwarded-allow-ips=*`. Depends on `postgres` and `redis` being healthy.
- **`frontend`:** Next.js 14 standalone container built with `ARG NEXT_PUBLIC_API_URL` to bake in the correct API endpoint.

### 3.2 Service Healthchecks
All services declare automated healthchecks:

```yaml
# Backend Health Check
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
  interval: 15s
  timeout: 5s
  retries: 3
  start_period: 10s

# Frontend Health Check
healthcheck:
  test: ["CMD-SHELL", "wget -q --spider http://localhost:3000/ || exit 1"]
  interval: 15s
  timeout: 5s
  retries: 3
  start_period: 20s
```

### 3.3 Running Docker Compose
```bash
# Build and launch in detached mode
docker compose up -d --build

# Verify container status and health
docker compose ps

# Tail unified logs
docker compose logs -f
```

---

## 4. Reverse Proxy & Trusted Proxy Security (NGINX / Traefik)

### 4.1 Anti-Spoofing & Trusted Proxy CIDR Filtering
To prevent IP spoofing attacks via manipulated `X-Forwarded-For` or `X-Real-IP` headers, Sentinel SOC implements a strict trusted proxy middleware:

1. When a request arrives, the backend inspects the immediate socket peer address (`client.host`).
2. If the peer address matches an entry in `TRUSTED_PROXIES` (e.g. `127.0.0.1`, `10.0.0.0/8`, `172.16.0.0/12`), the forwarded headers are trusted and the client IP is extracted.
3. If the peer address does **not** match a trusted proxy, forwarded headers are completely ignored, and the immediate peer address is used as the client IP.

Configure trusted proxies in `.env`:
```ini
TRUSTED_PROXIES=127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
```

### 4.2 Production NGINX Configuration
Below is a hardened NGINX configuration snippet for production deployments:

```nginx
# /etc/nginx/sites-available/sentinel-soc.conf

upstream sentinel_frontend {
    server 127.0.0.1:3000;
    keepalive 32;
}

upstream sentinel_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name soc.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name soc.example.com;

    ssl_certificate /etc/letsencrypt/live/soc.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/soc.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Frontend Route
    location / {
        proxy_pass http://sentinel_frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API Route
    location /api/ {
        proxy_pass http://sentinel_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90s;
    }

    # Backend Health Check
    location /health {
        proxy_pass http://sentinel_backend/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 5. Application Logging & Log Rotation

Sentinel SOC features structured logging with automatic file rotation via Python's standard `RotatingFileHandler`.

### 5.1 Configuration
- **Log Level:** Configurable via `LOG_LEVEL` (default: `INFO`, options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).
- **Log Destination:** Written concurrently to `sys.stdout` (for Docker container logs) and to a persistent log file defined by `LOG_FILE` (default: `logs/sentinel.log` or `/app/logs/sentinel.log`).
- **Rotation Parameters:** Maximum file size: **10 MB**, retaining **5 backup files** (`sentinel.log.1`, `sentinel.log.2`, etc.).

### 5.2 Log Formats
All log lines follow a standardized ISO-8601 timestamped format:
```text
%(asctime)s [%(levelname)s] %(name)s: %(message)s
```

Sensitive information (such as Bearer tokens, passwords, and raw enrollment keys) is scrubbed or omitted by default.

---

## 6. Health Monitoring & Observability

### 6.1 Database-Aware `/health` Endpoint
The `/health` endpoint performs a real-time `SELECT 1` ping against the active database engine:

```bash
curl http://localhost:8000/health
```

#### Healthy Response (HTTP 200):
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

#### Degraded Response (HTTP 503):
```json
{
  "status": "degraded",
  "app": "Sentinel SOC",
  "version": "1.0.0",
  "environment": "production",
  "database": {
    "status": "disconnected",
    "dialect": "postgresql",
    "error": "connection to server at 'localhost', port 5432 failed: Connection refused"
  }
}
```

---

## 7. Endpoint Sensor Agent Deployment

Endpoint sensors establish persistent telemetry collection and heartbeat monitoring.

### 7.1 Windows Sensor (NSSM Service)
```powershell
nssm install SentinelSensor "C:\sentinel-soc\.venv\Scripts\python.exe" "C:\sentinel-soc\sensors\windows\sentinel_sensor.py --server https://soc.example.com"
nssm set SentinelSensor AppDirectory "C:\sentinel-soc"
nssm set SentinelSensor Start SERVICE_AUTO_START
nssm start SentinelSensor
```

### 7.2 Linux Sensor (systemd Service)
```bash
sudo cp sensors/linux/sentinel-sensor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sentinel-sensor
```
