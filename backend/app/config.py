import os
from typing import Optional, List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices, field_validator, ValidationInfo

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="allow")

    APP_NAME: str = "Sentinel SOC"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV"))
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    
    # Security & Tokens
    SECRET_KEY: str = Field(default="sentinel-soc-insecure-dev-key-change-in-production-1234567890")
    ALGORITHM: str = Field(default="HS256", validation_alias=AliasChoices("ALGORITHM", "JWT_ALGORITHM"))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_production_secret_key(cls, v: str, info: ValidationInfo) -> str:
        env = (info.data.get("ENVIRONMENT") if hasattr(info, "data") else None) or os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "development"
        if str(env).lower() == "production":
            insecure_keys = [
                "sentinel-soc-insecure-dev-key-change-in-production-1234567890",
                "sentinel_soc_super_secret_development_key_min_32_bytes_long!!",
                "sentinel_soc_super_secret_production_key_min_32_bytes_long!!",
                "change-me",
            ]
            if not v or not v.strip() or v in insecure_keys or len(v.strip()) < 32:
                raise ValueError(
                    "CRITICAL PRODUCTION SECURITY ERROR: Production deployment cannot use a default or weak SECRET_KEY. "
                    "You must configure a private, high-entropy 32+ byte key via the SECRET_KEY environment variable."
                )
        return v
    
    # Initial Administrator Credentials (Bootstrap / First-Run Setup)
    INITIAL_ADMIN_EMAIL: str = Field(
        default="admin@sentinelsoc.com",
        validation_alias=AliasChoices("INITIAL_ADMIN_EMAIL", "ADMIN_EMAIL")
    )
    INITIAL_ADMIN_PASSWORD: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("INITIAL_ADMIN_PASSWORD", "ADMIN_PASSWORD")
    )

    @field_validator("INITIAL_ADMIN_PASSWORD")
    @classmethod
    def validate_production_admin_password(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        env = (info.data.get("ENVIRONMENT") if hasattr(info, "data") else None) or os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "development"
        is_prod = str(env).lower() == "production"
        if is_prod:
            insecure_passwords = [
                "sentineladmin123!",
                "admin1234567890",
                "password12345678",
                "change-me-immediately",
                "changeme12345678",
                "sentinel_admin_password",
                "sentineladmin123",
            ]
            if not v or not v.strip():
                raise ValueError(
                    "CRITICAL PRODUCTION SECURITY ERROR: INITIAL_ADMIN_PASSWORD must be explicitly provided in production. "
                    "You must configure a strong password (minimum 16 characters) via the INITIAL_ADMIN_PASSWORD or ADMIN_PASSWORD environment variable."
                )
            v_clean = v.strip()
            if len(v_clean) < 16 or v_clean.lower() in insecure_passwords:
                raise ValueError(
                    f"CRITICAL PRODUCTION SECURITY ERROR: INITIAL_ADMIN_PASSWORD is too weak (length {len(v_clean)} < 16 or matches known insecure defaults). "
                    "Production administrator passwords must be at least 16 characters long."
                )
            return v_clean
        else:
            # Safe non-production fallback for local development / testing
            if not v or not v.strip():
                return "SentinelAdmin123!"
            return v.strip()

    # Database: Supports SQLite (for zero-friction local/dev fallback) and PostgreSQL
    DATABASE_URL: str = Field(
        default="sqlite:///./sentinel.db",
        description="SQLAlchemy database connection string"
    )
    DB_POOL_SIZE: int = Field(default=10)
    DB_MAX_OVERFLOW: int = Field(default=20)
    DB_POOL_RECYCLE: int = Field(default=1800)
    DB_POOL_PRE_PING: bool = Field(default=True)
    
    # Redis & Background Tasks
    REDIS_URL: str = Field(default="redis://127.0.0.1:6379/0")
    REDIS_ENABLED: bool = Field(default=False)
    
    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        validation_alias=AliasChoices("BACKEND_CORS_ORIGINS", "CORS_ORIGINS")
    )

    @field_validator("BACKEND_CORS_ORIGINS")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    # Reverse Proxy & Trusted Proxy Security
    TRUSTED_PROXIES: Union[List[str], str] = Field(
        default=["127.0.0.1", "::1"],
        validation_alias=AliasChoices("TRUSTED_PROXIES", "TRUSTED_PROXIES_CIDRS")
    )

    @field_validator("TRUSTED_PROXIES")
    @classmethod
    def parse_trusted_proxies(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", validation_alias=AliasChoices("LOG_LEVEL", "LOGGING_LEVEL"))
    LOG_FILE: Optional[str] = Field(default="logs/sentinel.log")

    # AI Provider: Free Tier & Local Only
    AI_PROVIDER: str = Field(default="none")  # "gemini", "local", "none", "fallback"
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    GEMINI_MODEL: str = Field(default="gemini-1.5-flash")
    LOCAL_AI_BASE_URL: str = Field(
        default="http://localhost:11434/v1",
        validation_alias=AliasChoices("LOCAL_AI_BASE_URL", "LOCAL_AI_URL")
    )
    LOCAL_AI_MODEL: str = Field(default="llama3.2")
    AI_DAILY_QUOTA_LIMIT: int = Field(default=1000)

    @field_validator("LOCAL_AI_BASE_URL", mode="before")
    @classmethod
    def normalize_local_ai_url(cls, v: str) -> str:
        if isinstance(v, str) and v.strip():
            v = v.strip().rstrip("/")
            if not v.endswith("/v1"):
                v = f"{v}/v1"
        return v
    
    # Threat Intelligence Providers (Optional / Free-Tier)
    ABUSEIPDB_API_KEY: Optional[str] = Field(default=None)
    ALIENVAULT_OTX_KEY: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("ALIENVAULT_OTX_KEY", "OTX_API_KEY")
    )
    GREYNOISE_API_KEY: Optional[str] = Field(default=None)
    SPAMHAUS_DQS_KEY: Optional[str] = Field(default=None)
    THREAT_INTEL_CACHE_TTL_HOURS: int = Field(default=6)
    
    # Email / Notifications (Safe Dev Fallback)
    EMAIL_ENABLED: bool = Field(default=False, validation_alias=AliasChoices("EMAIL_ENABLED", "SMTP_ENABLED"))
    SMTP_HOST: Optional[str] = Field(default=None)
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: Optional[str] = Field(default=None)
    SMTP_PASSWORD: Optional[str] = Field(default=None)
    EMAILS_FROM_NAME: str = "Sentinel SOC"
    EMAILS_FROM_EMAIL: str = Field(
        default="alerts@sentinel.local",
        validation_alias=AliasChoices("EMAILS_FROM_EMAIL", "SMTP_FROM")
    )
    
    # Sensors
    SENSOR_HEARTBEAT_TIMEOUT_SECONDS: int = 120
    SENSOR_TOKEN_EXPIRY_HOURS: int = 48
    
    # AWS Integration (Disabled by default, optional)
    AWS_ENABLED: bool = Field(default=False)
    AWS_REGION: str = "us-east-1"
    AWS_ROLE_ARN: Optional[str] = None

settings = Settings()
