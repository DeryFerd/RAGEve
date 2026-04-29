"""
Authentication utilities: password hashing, JWT encode/decode, email sending.
"""

from __future__ import annotations

import logging
import smtplib
import uuid
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from backend.config import settings

_log = logging.getLogger(__name__)

# Password hashing context (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def generate_verification_token() -> str:
    """Generate a URL-safe verification token."""
    return str(uuid.uuid4().hex)  # 32 hex characters


def create_access_token(user_id: str, username: str, is_admin: bool = False) -> str:
    """Create a JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "user_id": user_id,
        "username": username,
        "is_admin": is_admin,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT access token. Returns payload dict or None if invalid."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"],
            options={"verify_exp": True},
        )
        if payload.get("type") != "access":
            _log.warning("Invalid token type: %s", payload.get("type"))
            return None
        return payload
    except jwt.ExpiredSignatureError:
        _log.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        _log.warning("Invalid token: %s", e)
        return None


async def send_verification_email(to_email: str, token: str) -> None:
    """
    Send email verification link to the user.

    In development (SMTP_DEV_MODE=console), prints the link to stdout.
    In production (SMTP_DEV_MODE=smtp), sends via SMTP.
    """
    verification_url = f"{settings.frontend_url}/api/auth/verify?token={token}"
    subject = "Verify your RAGEve account"
    body = f"""
    Hello,

    Thank you for registering with RAGEve!

    Please click the link below to verify your email address:

    {verification_url}

    This link will expire in 24 hours.

    If you did not create an account, please ignore this email.

    Best regards,
    RAGEve Team
    """.strip()

    if settings.smtp_dev_mode == "console":
        _log.info("[DEV MODE] Verification email to %s:", to_email)
        _log.info("Subject: %s", subject)
        _log.info("Body:\n%s", body)
        _log.info("Verification URL: %s", verification_url)
        return

    # Production: send via SMTP
    if not all([settings.smtp_host, settings.smtp_user, settings.smtp_password]):
        raise ValueError(
            "SMTP configuration incomplete: set SMTP_HOST, SMTP_USER, SMTP_PASSWORD"
        )

    # Assert non-None for mypy
    assert settings.smtp_user is not None
    assert settings.smtp_password is not None

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        _log.info("Verification email sent to %s", to_email)
    except Exception as e:
        _log.error("Failed to send verification email to %s: %s", to_email, e)
        raise
