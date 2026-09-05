from __future__ import annotations

from typing import Any
import re


# High-level provider health
ACTIVE = "ACTIVE"
ACTIVE_ANONYMOUS = "ACTIVE_ANONYMOUS"
AUTH_REQUIRED = "AUTH_REQUIRED"
LICENSE_REQUIRED = "LICENSE_REQUIRED"
LOCAL_AVAILABLE = "LOCAL_AVAILABLE"
LOCAL_UNAVAILABLE = "LOCAL_UNAVAILABLE"
UNAVAILABLE = "UNAVAILABLE"
DEGRADED = "DEGRADED"
DISABLED = "DISABLED"
ERROR = "ERROR"

# Auth status
AUTH_AUTHENTICATED = "AUTHENTICATED"
AUTH_ANONYMOUS = "ANONYMOUS"
AUTH_NOT_REQUIRED = "NOT_REQUIRED"
AUTH_REQUIRED_STATUS = "AUTH_REQUIRED"
AUTH_LICENSE_REQUIRED = "LICENSE_REQUIRED"
AUTH_NOT_APPLICABLE = "NOT_APPLICABLE"
AUTH_UNKNOWN = "UNKNOWN"

# Provider type
TYPE_HTTP = "http"
TYPE_LOCAL_IMPORT = "local_import"

MAIN_ROLE = {
    "tradingview": "Intraday OHLCV",
    "yahoo": "Daily/Historical",
    "egid": "Depth/Trades/Feed",
    "investor_egx": "Universe/Fundamentals",
    "borsa": "Fallback quotes/universe",
}

_NETWORK_FAILURE_MARKERS = (
    "timed out",
    "timeout",
    "connection refused",
    "connection reset",
    "name or service not known",
    "nodename nor servname",
    "failed to resolve",
    "network is unreachable",
    "host unreachable",
    "name resolution",
    "max retries exceeded",
    "temporarily unavailable",
    "ssl:",
    "certificate_verify_failed",
    "certificate verify failed",
    "failed to establish a new connection",
)


def extract_http_status(message: str | None, explicit: int | None = None) -> int | None:
    if explicit is not None:
        return explicit
    if not message:
        return None
    m = re.search(r"HTTP\s+(\d{3})", message, re.I)
    if m:
        return int(m.group(1))
    return None


def is_auth_http(status: int | None) -> bool:
    return status in (401, 403)


def is_network_failure(message: str | None, http_status: int | None = None) -> bool:
    """True only for transport-level failures. HTTP 401/403 are reachable."""
    if is_auth_http(http_status):
        return False
    if http_status is not None:
        # Any HTTP response means the host responded at the network layer.
        return False
    text = (message or "").lower()
    return any(marker in text for marker in _NETWORK_FAILURE_MARKERS)


def classify_http_reachability(message: str | None, http_status: int | None = None) -> bool | None:
    """
    Return True/False/None for network reachability.
    401/403 => True; timeout/DNS/TLS => False; unknown => None.
    """
    status = extract_http_status(message, http_status)
    if is_auth_http(status):
        return True
    if status is not None:
        return True
    if is_network_failure(message, status):
        return False
    return None


def auth_label(auth_status: str | None) -> str:
    return {
        AUTH_AUTHENTICATED: "Authenticated",
        AUTH_ANONYMOUS: "Anonymous (not required)",
        AUTH_NOT_REQUIRED: "Not required",
        AUTH_REQUIRED_STATUS: "Auth required",
        AUTH_LICENSE_REQUIRED: "License required",
        AUTH_NOT_APPLICABLE: "N/A",
        AUTH_UNKNOWN: "Unknown",
        None: "Unknown",
    }.get(auth_status or AUTH_UNKNOWN, auth_status or "Unknown")


def reachable_label(reachable: bool | None) -> str:
    if reachable is True:
        return "Yes"
    if reachable is False:
        return "No"
    return "N/A"


def serialize_status_for_display(st: dict[str, Any]) -> dict[str, Any]:
    """Human-facing row; preserves null/N/A for local adapters."""
    auth = st.get("auth_status") or AUTH_UNKNOWN
    return {
        "provider": st.get("name") or st.get("provider"),
        "state": st.get("health_state") or "UNKNOWN",
        "auth": auth_label(auth),
        "auth_status": auth,
        "reachable": reachable_label(st.get("reachable")),
        "reachable_raw": st.get("reachable"),
        "authenticated": st.get("authenticated"),
        "main_role": st.get("main_role") or MAIN_ROLE.get(st.get("name") or st.get("provider") or "", ""),
        "mode": st.get("mode"),
        "provider_type": st.get("provider_type"),
        "latency_ms": st.get("latency_ms"),
        "last_http_status": st.get("last_http_status"),
        "last_error": st.get("last_error"),
        "notes": st.get("notes"),
        "enabled": st.get("enabled"),
        "capabilities": st.get("capabilities") or {},
        "last_success": st.get("last_success"),
        "last_checked": st.get("last_checked"),
        "latest_source_timestamp": st.get("latest_source_timestamp"),
    }
