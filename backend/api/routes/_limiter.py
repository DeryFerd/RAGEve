"""
Rate limiter shared across all route modules.
Uses X-Forwarded-For aware IP extraction when TRUSTED_PROXY_COUNT > 0.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.config_loader import settings


def _get_client_ip(request) -> str:
    """
    Return the real client IP, accounting for trusted reverse proxies.

    When TRUSTED_PROXY_COUNT > 0, the function reads X-Forwarded-For and
    returns the leftmost IP after removing the trusted proxy IPs from the
    right end of the chain. This assumes that the leftmost IP is the original
    client, and each trusted proxy appends its own IP to the right.

    For example, with X-Forwarded-For: "client, proxy1, proxy2" and
    TRUSTED_PROXY_COUNT=2 (trusting proxy1 and proxy2), the function
    returns "client".

    Set TRUSTED_PROXY_COUNT=0 to disable proxy awareness and use the
    direct remote address.
    """
    try:
        proxy_count = int(settings.trusted_proxy_count)
    except (ValueError, TypeError):
        proxy_count = 0

    if proxy_count <= 0:
        return get_remote_address(request)

    fwd = request.headers.get("X-Forwarded-For", "")
    if not fwd:
        return get_remote_address(request)

    ips = [ip.strip() for ip in fwd.split(",")]
    # Remove empty strings
    ips = [ip for ip in ips if ip]

    if not ips:
        return get_remote_address(request)

    # If we have more IPs than the number of trusted proxies, strip the
    # trusted proxy IPs from the right and return the IP just before them.
    # This is the rightmost untrusted IP (often the original client).
    if len(ips) > proxy_count:
        idx = len(ips) - proxy_count - 1
        return ips[idx]

    # All IPs are trusted (or fewer IPs than trusted proxies).
    # Return the first IP as the best guess for the client.
    return ips[0]


# Shared rate limiter instance used by all route modules.
# Active only when API_KEY is configured; otherwise no-op.
limiter = Limiter(key_func=_get_client_ip, enabled=bool(settings.api_key))
