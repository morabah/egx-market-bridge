from __future__ import annotations

import json
import zipfile
from pathlib import Path

from egxbridge.egxapi_probe import (
    dashboard_is_sample_only,
    interpret_status,
    request_had_authorization,
    sanitize_headers,
    sanitize_body,
    should_create_provider,
)


def test_401_reachable_auth_required():
    r = interpret_status(401)
    assert r["reachable"] is True
    assert r["authentication_required"] is True
    assert r["label"] == "AUTH_REQUIRED"


def test_403_reachable_forbidden_or_auth():
    r = interpret_status(403)
    assert r["reachable"] is True
    assert r["authentication_required"] is True


def test_sample_dashboard_rejected():
    html = "<html><body><h1>Sample data</h1><p>Not live market data</p></body></html>"
    assert dashboard_is_sample_only(html) is True
    assert should_create_provider(False) is False


def test_no_authorization_detection():
    assert request_had_authorization({"Accept": "application/json"}) is False
    assert request_had_authorization({"Authorization": "Bearer x"}) is True
    assert request_had_authorization({"authorization": "Bearer x"}) is True


def test_sanitize_redacts_tokens_and_cookies():
    h = sanitize_headers({
        "Content-Type": "application/json",
        "Authorization": "Bearer secret",
        "Set-Cookie": "session=abc",
        "X-RateLimit-Limit": "1000",
    })
    assert h["Authorization"] == "[REDACTED]"
    assert h["Set-Cookie"] == "[REDACTED]"
    assert h["X-RateLimit-Limit"] == "1000"
    body = sanitize_body('Authorization: Bearer egx_live_ABCDEFG token')
    assert "ABCDEFG" not in body
    assert "[REDACTED]" in body


def test_authenticated_only_does_not_create_provider():
    assert should_create_provider(False) is False
    assert should_create_provider(True) is True


def test_zip_generation_shape(tmp_path: Path):
    root = tmp_path / "egxapi_probe"
    root.mkdir()
    (root / "probe_summary.json").write_text(json.dumps({"overall_decision": "API KEY REQUIRED"}), encoding="utf-8")
    zp = tmp_path / "egxapi_probe.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        for f in root.rglob("*"):
            if f.is_file():
                zf.write(f, arcname=str(Path("egxapi_probe") / f.relative_to(root)))
    assert zp.exists()
    with zipfile.ZipFile(zp) as zf:
        assert "egxapi_probe/probe_summary.json" in zf.namelist()
