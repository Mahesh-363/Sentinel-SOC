#!/usr/bin/env python3
"""
Sentinel SOC — Secure Administrator Password Reset & Recovery CLI Tool

This script allows an authorized system administrator to securely reset the
password for an administrator account in the local Sentinel SOC environment.

Security Features:
- Does NOT hardcode passwords.
- Uses getpass to prompt for passwords securely without echoing to terminal.
- Enforces minimum password strength requirements (min 8 characters).
- Hashes password using the project's standard bcrypt implementation.
- Preserves the existing administrator account ID, organization memberships, and assets.
- Appends an audit entry recording the administrative reset event.
- Never prints passwords or password hashes to console or logs.

Usage:
    Interactive (recommended):
        python scripts/reset_admin_password.py

    Specific user:
        python scripts/reset_admin_password.py --email admin@sentinelsoc.com

    Automated / Non-interactive (CI/testing only):
        python scripts/reset_admin_password.py --email admin@sentinelsoc.com --password "NewPassword123!"
"""

import sys
import os
import argparse
import getpass
from datetime import datetime

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.database import SessionLocal
from backend.app.models.auth import User, AuditLog
from backend.app.core.security import hash_password


def reset_password(email: str, new_password: str, db=None) -> bool:
    """Resets the password for the specified user and records an audit log entry."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        user = db.query(User).filter(User.email == email.lower().strip()).first()
        if not user:
            print(f"[ERROR] User with email '{email}' not found in the database.", file=sys.stderr)
            return False

        if not user.is_active:
            print(f"[ERROR] Cannot reset password: user account '{email}' is deactivated.", file=sys.stderr)
            return False

        # Hash using project's standard bcrypt implementation
        user.hashed_password = hash_password(new_password)
        user.updated_at = datetime.utcnow()

        # Record audit log
        audit = AuditLog(
            organization_id=None,
            user_id=user.id,
            user_email=user.email,
            action="ADMIN_PASSWORD_RESET_CLI",
            target_type="user",
            target_id=user.id,
            details=f"Administrator password reset via CLI tool for user {user.email}"
        )
        db.add(audit)
        db.commit()
        db.refresh(user)
        return True
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Database error during password reset: {e}", file=sys.stderr)
        return False
    finally:
        if close_db:
            db.close()


def find_default_admin() -> str:
    """Finds the primary administrator email in the database."""
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.is_platform_admin == True, User.is_active == True).first()
        if admin:
            return admin.email
        any_user = db.query(User).filter(User.is_active == True).first()
        if any_user:
            return any_user.email
        return "admin@sentinelsoc.com"
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Sentinel SOC — Secure Administrator Password Reset Utility"
    )
    parser.add_argument(
        "--email",
        type=str,
        default=None,
        help="Email address of the administrator account to reset (defaults to primary platform admin)"
    )
    parser.add_argument(
        "--password",
        type=str,
        default=None,
        help="New password (for non-interactive automation only; if omitted, you will be prompted securely)"
    )

    args = parser.parse_args()

    target_email = args.email or find_default_admin()

    print("=" * 70)
    print(" Sentinel SOC — Administrator Password Recovery Utility")
    print("=" * 70)
    print(f"Target Account: {target_email}\n")

    if args.password:
        new_password = args.password
    else:
        try:
            new_password = getpass.getpass("Enter new administrator password: ")
            if not new_password:
                print("[ERROR] Password cannot be empty.", file=sys.stderr)
                sys.exit(1)

            confirm_password = getpass.getpass("Confirm new administrator password: ")
            if new_password != confirm_password:
                print("[ERROR] Passwords do not match. Aborting.", file=sys.stderr)
                sys.exit(1)
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled by user.", file=sys.stderr)
            sys.exit(1)

    if len(new_password) < 8:
        print("[ERROR] Password must be at least 8 characters long for security compliance.", file=sys.stderr)
        sys.exit(1)

    success = reset_password(target_email, new_password)
    if success:
        print(f"\n[SUCCESS] Password for '{target_email}' has been successfully reset.")
        print("You can now log in at: http://localhost:3000/login or via the API.")
        print("=" * 70)
        sys.exit(0)
    else:
        print(f"\n[FAILED] Could not reset password for '{target_email}'.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
