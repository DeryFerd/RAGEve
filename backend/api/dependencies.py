"""
Shared FastAPI dependencies.

Provides:
- get_current_user: Authenticates via JWT cookie and returns the User.
"""

from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, Request, status

from backend.models_peewee.user import User
from backend.services.auth import decode_access_token
from backend.services.database import run_db_operation
from backend.services.tenant_user_store import get_tenant_user_store

__all__ = ["get_current_user"]


async def get_current_user(
    request: Request,
    access_token: str | None = Cookie(default=None, alias="access_token"),
) -> User:
    """
    Dependency that extracts and validates JWT from HttpOnly cookie.
    Returns the authenticated User object.

    Raises:
        HTTPException: 401 if no token, invalid token, or user not found/inactive.
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_access_token(access_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_store = get_tenant_user_store()
    user = await run_db_operation(user_store.get_user, payload["user_id"])
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )

    # Attach user to request.state for downstream access if needed
    request.state.user = user
    return user
