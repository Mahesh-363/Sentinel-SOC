import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Any, Dict
import bcrypt
import jwt
from backend.app.config import settings

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None

def hash_token(token: str) -> str:
    """Hashes API key or sensor token using SHA-256 for secure storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def generate_enrollment_token() -> str:
    """Generates a high-entropy single-use sensor enrollment token."""
    return f"stk_{secrets.token_urlsafe(32)}"

def generate_sensor_api_key() -> str:
    """Generates a sensor API key for regular telemetry authentication."""
    return f"sak_{secrets.token_hex(32)}"
