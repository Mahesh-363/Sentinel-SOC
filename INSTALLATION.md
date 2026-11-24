# SENTINEL SOC — Installation & Setup Guide

For the full detailed installation manual, refer to [docs/INSTALLATION.md](docs/INSTALLATION.md).

---

## ⚡ Quickstart Summary

### 1. Requirements
- Python 3.11+
- Node.js 18+ (Node 20 LTS recommended)
- (Optional) PostgreSQL 14+ / Docker

### 2. Configure Environment
```bash
# Windows
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

### 3. Backend Setup
```bash
# Setup virtual environment
python -m venv .venv
# Activate:
# Windows: .\.venv\Scripts\Activate.ps1
# Linux:   source .venv/bin/activate

pip install -r backend/requirements.txt
python -m backend.app.db.seed
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 5. Access Application
- Web UI: [http://localhost:3000](http://localhost:3000)
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)
- Local Development Credentials: `admin@sentinelsoc.com` / `SentinelAdmin123!` *(Mandatory rotation enforced on first login. In production, configure `INITIAL_ADMIN_PASSWORD`)*

For production PostgreSQL setup, Alembic migrations, Docker Compose, and sensor deployment, see [docs/INSTALLATION.md](docs/INSTALLATION.md).
