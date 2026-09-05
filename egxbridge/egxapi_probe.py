"""Read-only EGXAPI connectivity / documentation probe helpers."""
from __future__ import annotations

from typing import Any
import json
import re
from pathlib import Path


SENSITIVE_HEADER_KEYS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
    "x-session-id",
    "x-csrf-token",
}


def sanitize_headers(headers: dict[str, Any] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in (headers or {}).items():
        lk = str(k).lower()
        if lk in SENSITIVE_HEADER_KEYS or "token" in lk or "cookie" in lk or "auth" in lk:
            out[str(k)] = "[REDACTED]"
        else:
            out[str(k)] = str(v)[:500]
    return out


def sanitize_body(text: str | None, limit: int = 2000) -> str:
    if not text:
        return ""
    cleaned = text
    cleaned = re.sub(r"(?i)(authorization\s*:\s*bearer\s+)(\S+)", r"\1[REDACTED]", cleaned)
    cleaned = re.sub(r"(?i)(egx_(?:live|paper|test)_)[A-Za-z0-9]+", r"\1[REDACTED]", cleaned)
    cleaned = re.sub(r"(?i)(\"?(?:access_token|refresh_token|api_key|session_id)\"?\s*[:=]\s*[\"']?)([^\"'\s,}]+)",
                     r"\1[REDACTED]", cleaned)
    return cleaned[:limit]


def interpret_status(code: int | None) -> dict[str, Any]:
    if code is None:
        return {"reachable": False, "authentication_required": None, "label": "NO_RESPONSE"}
    if code == 200:
        return {"reachable": True, "authentication_required": False, "label": "OK_POSSIBLE_ANONYMOUS"}
    if code == 401:
        return {"reachable": True, "authentication_required": True, "label": "AUTH_REQUIRED"}
    if code == 403:
        return {"reachable": True, "authentication_required": True, "label": "FORBIDDEN_OR_AUTH_REQUIRED"}
    if code == 404:
        return {"reachable": True, "authentication_required": None, "label": "NOT_FOUND"}
    if code == 429:
        return {"reachable": True, "authentication_required": None, "label": "RATE_LIMITED"}
    if 500 <= code <= 599:
        return {"reachable": True, "authentication_required": None, "label": "SERVER_ERROR"}
    return {"reachable": True, "authentication_required": None, "label": f"HTTP_{code}"}


def dashboard_is_sample_only(html: str) -> bool:
    low = (html or "").lower()
    return ("sample data" in low) or ("sample-data" in low) or ("sample_data" in low)


def request_had_authorization(prepared_headers: dict[str, Any] | None) -> bool:
    for k in (prepared_headers or {}):
        if str(k).lower() == "authorization":
            return True
    return False


def should_create_provider(anonymous_market_data: bool) -> bool:
    """Provider stub only when genuine anonymous market data was returned."""
    return bool(anonymous_market_data)


def jdump(path: Path, obj: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
