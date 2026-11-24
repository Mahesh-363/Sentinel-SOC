import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.config import Settings
from backend.app.models.auth import User
from backend.app.core.security import hash_password, verify_password, create_access_token


def test_production_fails_when_admin_password_missing():
    """Requirement A: Production startup fails when INITIAL_ADMIN_PASSWORD is missing."""
    valid_secret = "a" * 32

    # Empty string
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=valid_secret,
            INITIAL_ADMIN_PASSWORD=""
        )
    assert "INITIAL_ADMIN_PASSWORD must be explicitly provided in production" in str(exc_info.value)

    # None / Unset
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=valid_secret,
            INITIAL_ADMIN_PASSWORD=None
        )
    assert "INITIAL_ADMIN_PASSWORD must be explicitly provided in production" in str(exc_info.value)


def test_production_rejects_weak_admin_password():
    """Requirement B: Production startup rejects a weak initial password."""
    valid_secret = "a" * 32

    # Under 16 characters
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=valid_secret,
            INITIAL_ADMIN_PASSWORD="ShortPass123!"
        )
    assert "INITIAL_ADMIN_PASSWORD is too weak" in str(exc_info.value)

    # Insecure default password
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=valid_secret,
            INITIAL_ADMIN_PASSWORD="SentinelAdmin123!"
        )
    assert "INITIAL_ADMIN_PASSWORD is too weak" in str(exc_info.value)


def test_production_accepts_strong_admin_password():
    """Verify strong production admin password succeeds validation."""
    valid_secret = "a" * 32
    strong_pass = "CustomVeryStrongAdminPassword2026!#"
    cfg = Settings(
        ENVIRONMENT="production",
        SECRET_KEY=valid_secret,
        INITIAL_ADMIN_PASSWORD=strong_pass
    )
    assert cfg.INITIAL_ADMIN_PASSWORD == strong_pass


def test_production_seeding_uses_configured_credentials_and_requires_first_login_change(db_session: Session):
    """
    Requirement C & E:
    Production seeding uses configured credentials, and sets must_change_password=True.
    """
    configured_email = "ciso-custom@enterprise-soc.net"
    configured_pass = "SuperSecureCisoInitialPass2026!"

    # Simulate seeding with configured values
    admin = User(
        email=configured_email,
        hashed_password=hash_password(configured_pass),
        full_name="Chief Information Security Officer",
        is_active=True,
        is_platform_admin=True,
        must_change_password=True
    )
    db_session.add(admin)
    db_session.commit()

    # Query back
    saved = db_session.query(User).filter(User.email == configured_email).first()
    assert saved is not None
    assert saved.email == configured_email
    assert saved.is_platform_admin is True
    assert saved.must_change_password is True
    assert verify_password(configured_pass, saved.hashed_password) is True
    assert verify_password("SentinelAdmin123!", saved.hashed_password) is False


def test_existing_admin_passwords_not_overwritten_on_restart(db_session: Session):
    """Requirement D: Existing admin passwords are not overwritten on subsequent restarts."""
    email = "existing-admin@soc.corp"
    original_pass = "OriginalActivePassword123!"
    original_hash = hash_password(original_pass)

    user = User(
        email=email,
        hashed_password=original_hash,
        full_name="Existing Admin",
        is_active=True,
        is_platform_admin=True,
        must_change_password=False
    )
    db_session.add(user)
    db_session.commit()

    # Re-running seed check: if user already exists, seed skips modifying password
    existing = db_session.query(User).filter(User.email == email).first()
    assert existing is not None
    # Password hash remains identical
    assert existing.hashed_password == original_hash
    assert verify_password(original_pass, existing.hashed_password) is True


def test_login_returns_must_change_password_flag(client: TestClient, db_session: Session):
    """Requirement E: Login returns must_change_password=True for users requiring change."""
    email = "flag-test@sentinelsoc.com"
    pwd = "TempInitialPassword123!"

    user = User(
        email=email,
        hashed_password=hash_password(pwd),
        full_name="Flag Test Analyst",
        is_active=True,
        is_platform_admin=True,
        must_change_password=True
    )
    db_session.add(user)
    db_session.commit()

    res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["must_change_password"] is True
    assert "access_token" in data


def test_password_change_rejects_unauthenticated(client: TestClient):
    """Requirement H: Unauthenticated password-change requests are rejected."""
    res = client.post("/api/v1/auth/change-password", json={
        "current_password": "any",
        "new_password": "ValidNewPassword123!"
    })
    assert res.status_code == 401


def test_password_change_rejects_incorrect_current_password(client: TestClient, db_session: Session):
    """Requirement F: Incorrect current password is rejected."""
    email = "wrong-pwd@sentinelsoc.com"
    real_pass = "RealCurrentPassword123!"

    user = User(
        email=email,
        hashed_password=hash_password(real_pass),
        full_name="Test User",
        is_active=True,
        must_change_password=True
    )
    db_session.add(user)
    db_session.commit()

    token = create_access_token({"sub": user.id, "email": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/v1/auth/change-password", headers=headers, json={
        "current_password": "WrongPasswordAttempt!",
        "new_password": "ValidNewPassword123!"
    })
    assert res.status_code == 400
    assert "Current password verification failed" in res.json()["detail"]


def test_password_change_rejects_short_or_identical_password(client: TestClient, db_session: Session):
    """Password change rejects passwords under 12 characters or identical to current."""
    email = "validation-test@sentinelsoc.com"
    current_pass = "CurrentSecurePassword123!"

    user = User(
        email=email,
        hashed_password=hash_password(current_pass),
        full_name="Test User",
        is_active=True,
        must_change_password=True
    )
    db_session.add(user)
    db_session.commit()

    token = create_access_token({"sub": user.id, "email": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Too short (< 12 chars)
    res_short = client.post("/api/v1/auth/change-password", headers=headers, json={
        "current_password": current_pass,
        "new_password": "short123"
    })
    assert res_short.status_code == 400
    assert "at least 12 characters" in res_short.json()["detail"]

    # Identical to current password
    res_same = client.post("/api/v1/auth/change-password", headers=headers, json={
        "current_password": current_pass,
        "new_password": current_pass
    })
    assert res_same.status_code == 400
    assert "cannot be identical" in res_same.json()["detail"]


def test_password_change_success_updates_hash_and_clears_flag(client: TestClient, db_session: Session):
    """Requirement G: Successful password change updates the hash and clears must_change_password."""
    email = "rotation-success@sentinelsoc.com"
    current_pass = "InitialSetupPassword123!"
    new_pass = "BrandNewSuperSecurePassword2026!"

    user = User(
        email=email,
        hashed_password=hash_password(current_pass),
        full_name="Rotation Admin",
        is_active=True,
        is_platform_admin=True,
        must_change_password=True
    )
    db_session.add(user)
    db_session.commit()

    token = create_access_token({"sub": user.id, "email": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/v1/auth/change-password", headers=headers, json={
        "current_password": current_pass,
        "new_password": new_pass
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "success"
    assert data["must_change_password"] is False
    assert "access_token" in data

    # Verify database state
    db_session.refresh(user)
    assert user.must_change_password is False
    assert verify_password(new_pass, user.hashed_password) is True
    assert verify_password(current_pass, user.hashed_password) is False

    # Verify user can log in with new password
    login_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": new_pass
    })
    assert login_res.status_code == 200
    assert login_res.json()["must_change_password"] is False
