import os
import logging
from logging.handlers import RotatingFileHandler
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import settings
from backend.app.database import engine, Base
from backend.app.db.seed import seed_database
import backend.app.models

# Configure production-ready structured logging
log_handlers = [logging.StreamHandler()]
if settings.LOG_FILE:
    log_dir = os.path.dirname(settings.LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8"
    )
    log_handlers.append(file_handler)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=log_handlers
)
logger = logging.getLogger("sentinel.app")

# Routers
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.organizations import router as orgs_router
from backend.app.api.v1.dashboard import router as dashboard_router
from backend.app.api.v1.assets import router as assets_router
from backend.app.api.v1.sensors import router as sensors_router
from backend.app.api.v1.network import router as network_router
from backend.app.api.v1.ip_intelligence import router as ip_router
from backend.app.api.v1.events import router as events_router
from backend.app.api.v1.detections import router as detections_router
from backend.app.api.v1.incidents import router as incidents_router
from backend.app.api.v1.notifications import router as notifications_router
from backend.app.api.v1.ai_analyst import router as ai_analyst_router
from backend.app.api.v1.ai_helpdesk import router as ai_helpdesk_router
from backend.app.api.v1.response import router as response_router
from backend.app.api.v1.aws import router as aws_router
from backend.app.api.v1.simulation import router as simulation_router
from backend.app.api.v1.reports import router as reports_router
from backend.app.api.v1.admin import router as admin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure tables exist and default seed data is ready
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield
    # Shutdown: Clean up any background connections if needed

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sentinel Security Operations Center (SOC) — AI-assisted Security Operations Center platform.",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public Network Visibility Collector with strict trusted proxy validation
@app.middleware("http")
async def observe_public_traffic(request: Request, call_next):
    remote_host = request.client.host if request.client else "unknown"
    is_trusted_proxy = remote_host in settings.TRUSTED_PROXIES

    if is_trusted_proxy:
        forwarded_for = request.headers.get("x-forwarded-for")
        real_ip = request.headers.get("x-real-ip")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        elif real_ip:
            client_ip = real_ip.strip()
        else:
            client_ip = remote_host
    else:
        # Untrusted client socket: reject arbitrary client-supplied forwarded headers
        client_ip = remote_host

    request.state.client_ip = client_ip
    response = await call_next(request)
    return response

# Register API v1 Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(orgs_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=settings.API_V1_STR)
app.include_router(assets_router, prefix=settings.API_V1_STR)
app.include_router(sensors_router, prefix=settings.API_V1_STR)
app.include_router(network_router, prefix=settings.API_V1_STR)
app.include_router(ip_router, prefix=settings.API_V1_STR)
app.include_router(events_router, prefix=settings.API_V1_STR)
app.include_router(detections_router, prefix=settings.API_V1_STR)
app.include_router(incidents_router, prefix=settings.API_V1_STR)
app.include_router(notifications_router, prefix=settings.API_V1_STR)
app.include_router(ai_analyst_router, prefix=settings.API_V1_STR)
app.include_router(ai_helpdesk_router, prefix=settings.API_V1_STR)
app.include_router(response_router, prefix=settings.API_V1_STR)
app.include_router(aws_router, prefix=settings.API_V1_STR)
app.include_router(simulation_router, prefix=settings.API_V1_STR)
app.include_router(reports_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)

@app.get("/health")
def health():
    db_status = "connected"
    db_error = None
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "error"
        db_error = str(e)

    overall_status = "healthy" if db_status == "connected" else "degraded"
    status_code = 200 if overall_status == "healthy" else 503

    content = {
        "status": overall_status,
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": {
            "status": db_status,
            "dialect": engine.dialect.name,
            "error": db_error
        }
    }
    return JSONResponse(status_code=status_code, content=content)

@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }
