"""
Unit tests for backend.services.auth.

Run: uv run python test/test_auth.py
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root is in path
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from datetime import datetime, timedelta, timezone
from backend.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    generate_verification_token,
)
from backend.config import settings


def test_password_hashing():
    password = "secure_password_123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)
    print("✓ Password hashing works")


def test_verification_token():
    token = generate_verification_token()
    # Should be a 32-character hex string (UUID4 hex)
    assert isinstance(token, str)
    assert len(token) == 32
    # Tokens should be unique
    token2 = generate_verification_token()
    assert token != token2
    print("✓ Verification token generation works")


def test_jwt_token():
    # Set a known secret for testing
    settings.jwt_secret_key = "test_secret_1234567890"
    settings.jwt_expire_minutes = 5

    user_id = "user-123"
    username = "testuser"
    is_admin = False

    token = create_access_token(user_id=user_id, username=username, is_admin=is_admin)
    assert isinstance(token, str)
    assert len(token) > 0

    # Decode and verify payload
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["user_id"] == user_id
    assert payload["username"] == username
    assert payload["is_admin"] == is_admin
    assert "exp" in payload
    assert "iat" in payload
    assert payload["type"] == "access"
    print("✓ JWT token creation and decoding works")

    # Test expiry (we can't easily test time in unit test, but we can check structure)
    exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    # Should be roughly now + 5 minutes
    delta = exp_time - now
    assert 280 < delta.total_seconds() < 310  # allow some slack
    print("✓ JWT expiry time correct")


def test_jwt_invalid():
    settings.jwt_secret_key = "test_secret_1234567890"

    # Invalid token (wrong secret)
    invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiIn0.signature"
    payload = decode_access_token(invalid_token)
    assert payload is None
    print("✓ Invalid token returns None")

    # Expired token (manually create an expired token)
    from jose import jwt
    expired_payload = {
        "user_id": "user",
        "username": "test",
        "is_admin": False,
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=1),
        "type": "access",
    }
    expired_token = jwt.encode(expired_payload, settings.jwt_secret_key, algorithm="HS256")
    payload = decode_access_token(expired_token)
    assert payload is None
    print("✓ Expired token returns None")

    # Wrong token type
    wrong_type_payload = {
        "user_id": "user",
        "type": "refresh",  # not "access"
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    wrong_type_token = jwt.encode(wrong_type_payload, settings.jwt_secret_key, algorithm="HS256")
    payload = decode_access_token(wrong_type_token)
    assert payload is None
    print("✓ Wrong token type returns None")


def test_send_verification_email_dev_mode():
    # This is a simple smoke test that dev mode doesn't raise
    from backend.services import auth
    # Force dev mode
    original_dev_mode = settings.smtp_dev_mode
    settings.smtp_dev_mode = "console"
    try:
        # Should just log and not send email
        asyncio.run(auth.send_verification_email("test@example.com", "token123"))
        print("✓ send_verification_email in dev mode completes without error")
    finally:
        settings.smtp_dev_mode = original_dev_mode


def main():
    print("Running auth unit tests...")
    test_password_hashing()
    test_verification_token()
    test_jwt_token()
    test_jwt_invalid()
    test_send_verification_email_dev_mode()
    print("\nAll auth unit tests passed.")


if __name__ == "__main__":
    main()
