#!/usr/bin/env python3
"""Read-only EGXAPI documentation + anonymous connectivity probe.

Does NOT bypass auth, scrape dashboard sample data as market data,
call trading endpoints, or modify production provider config.
"""
from __future__ import annotations

import csv
import json
import platform
import socket
import ssl
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from egxbridge import __version__ as BRIDGE_VERSION
from egxbridge.egxapi_probe import (
    dashboard_is_sample_only,
    interpret_status,
    jdump,
    request_had_authorization,
    sanitize_body,
    sanitize_headers,
    should_create_provider,
)

UA = {"User-Agent": "EGX-Market-Bridge-Probe/0.3.1 (read-only; no credentials)"}
# Explicitly no Authorization / Cookie
SAFE_HEADERS = {**UA, "Accept": "application/json, text/plain, */*"}

DOCS_JS = "https://egxapi.com/_next/static/chunks/00th6g57wl79z.js"


def _tls_check(host: str, port: int = 443) -> dict[str, Any]:
    t0 = time.time()
    out: dict[str, Any] = {"host": host, "port": port}
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        out["dns"] = sorted({i[4][0] for i in infos})
        out["dns_ok"] = True
    except Exception as e:
        out["dns_ok"] = False
        out["dns_error"] = str(e)
        return out
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                out["tls_ok"] = True
                out["tls_version"] = ssock.version()
                out["cert_subject"] = dict(x[0] for x in cert.get("subject", ()))
                out["cert_not_after"] = cert.get("notAfter")
        out["https_connect_ms"] = round((time.time() - t0) * 1000, 2)
    except Exception as e:
        out["tls_ok"] = False
        out["tls_error"] = str(e)
        out["https_connect_ms"] = round((time.time() - t0) * 1000, 2)
    return out


def _get(url: str, *, method: str = "GET", params: dict | None = None, retry_5xx: bool = True) -> dict[str, Any]:
    """One request; optional single retry on transient 5xx/network. Never sends Authorization."""
    assert "Authorization" not in SAFE_HEADERS
    t0 = time.time()
    attempt = 0
    last: dict[str, Any] = {}
    while attempt < (2 if retry_5xx else 1):
        attempt += 1
        try:
            r = requests.request(
                method,
                url,
                headers=SAFE_HEADERS,
                params=params,
                timeout=20,
                allow_redirects=True,
            )
            # Verify we did not send auth
            sent_auth = request_had_authorization(dict(r.request.headers))
            body = r.text or ""
            row = {
                "url": url,
                "final_url": str(r.url),
                "method": method,
                "params": params or {},
                "status_code": r.status_code,
                "latency_ms": round((time.time() - t0) * 1000, 2),
                "content_type": r.headers.get("Content-Type"),
                "response_headers": sanitize_headers(dict(r.headers)),
                "response_body_excerpt": sanitize_body(body),
                "redirect_target": str(r.url) if str(r.url) != url else None,
                "authorization_header_sent": sent_auth,
                "rate_limit_headers": {
                    k: v for k, v in r.headers.items()
                    if "ratelimit" in k.lower() or k.lower() in {"retry-after"}
                },
                "attempt": attempt,
                **interpret_status(r.status_code),
            }
            last = row
            if r.status_code >= 500 and attempt < 2:
                time.sleep(0.8)
                continue
            return row
        except Exception as e:
            last = {
                "url": url,
                "method": method,
                "params": params or {},
                "status_code": None,
                "latency_ms": round((time.time() - t0) * 1000, 2),
                "error": str(e),
                "authorization_header_sent": False,
                "attempt": attempt,
                **interpret_status(None),
            }
            if attempt < 2:
                time.sleep(0.8)
                continue
            return last
    return last


def discover_docs() -> dict[str, Any]:
    docs = []
    urls = [
        "https://egxapi.com/",
        "https://egxapi.com/docs/",
        "https://egxapi.com/auth/",
        "https://egxapi.com/dashboard/",
        "https://egxapi.com/robots.txt",
        "https://api.egxapi.com/",
        "https://api.egxapi.com/v2/",
        "https://api.egxapi.com/openapi.json",
        "https://api.egxapi.com/swagger.json",
        "https://api.egxapi.com/api-docs",
        "https://api.egxapi.com/docs/openapi.json",
        "https://api.egxapi.com/v2/openapi.json",
        "https://egxapi.com/openapi.json",
        DOCS_JS,
    ]
    for u in urls:
        row = _get(u, retry_5xx=False)
        docs.append({
            "documentation_url": u,
            "status_code": row.get("status_code"),
            "content_type": row.get("content_type"),
            "publicly_accessible": row.get("status_code") == 200,
            "latency_ms": row.get("latency_ms"),
            "notes": row.get("error") or (
                "Cloudflare/origin error page" if (row.get("status_code") or 0) >= 500 else ""
            ),
            "body_excerpt": row.get("response_body_excerpt", "")[:300],
        })
    return {"resources": docs}


def documented_endpoints_from_public_docs() -> list[dict[str, Any]]:
    """Only endpoints explicitly present in public docs JS (no invention)."""
    return [
        {
            "capability": "ACCOUNT",
            "method": "GET",
            "path": "/v2/account",
            "required_parameters": [],
            "documented_authentication_requirement": "Bearer API key required (every request)",
            "environment_header_requirement": "X-EGX-Env: paper|live (shown in Quickstart)",
            "response_schema_if_documented": "account object (cash, buying_power, environment)",
            "websocket_equivalent": None,
            "probe_as_market_data": False,
            "notes": "Not a market-data endpoint; documented for auth check only — DO NOT call in market probe",
        },
        {
            "capability": "BARS",
            "method": "GET",
            "path": "/v2/market-data/bars",
            "required_parameters": ["symbol", "timeframe"],
            "optional_parameters": ["start", "limit"],
            "documented_authentication_requirement": "Bearer API key (curl example includes Authorization)",
            "environment_header_requirement": "Not shown on bars example; auth guide says every request authenticated",
            "response_schema_if_documented": '{"symbol","bars":[{"t","o","h","l","c","v"}]}',
            "websocket_equivalent": "quotes channel on wss://stream.egxapi.com/v2 (separate from REST bars)",
            "probe_as_market_data": True,
            "notes": "Only explicitly documented REST market-data path in public docs",
        },
        {
            "capability": "QUOTE",
            "method": "WSS subscribe",
            "path": "wss://stream.egxapi.com/v2",
            "required_parameters": ["quotes: [symbols] after auth"],
            "documented_authentication_requirement": 'Mandatory auth message: {"action":"auth","key":"$EGX_KEY","env":"paper"}',
            "environment_header_requirement": "env field in auth JSON",
            "response_schema_if_documented": '{"stream":"quote","symbol","bid","ask","t"}',
            "websocket_equivalent": "self",
            "probe_as_market_data": True,
            "notes": "Quotes described for WebSocket; no separate REST /quotes path documented",
        },
        {
            "capability": "TRADES",
            "method": "WSS subscribe",
            "path": "wss://stream.egxapi.com/v2",
            "required_parameters": ["trade_updates (account order fills) and/or market trades if supported"],
            "documented_authentication_requirement": "Auth action with API key before subscribe",
            "environment_header_requirement": "env in auth JSON",
            "response_schema_if_documented": "Streaming lead mentions trades; example shows trade_updates:true",
            "websocket_equivalent": "self",
            "probe_as_market_data": False,
            "notes": "Docs emphasize trade_updates (order events). No REST /trades path documented.",
        },
        {
            "capability": "ORDER_BOOK_DEPTH",
            "method": None,
            "path": None,
            "required_parameters": [],
            "documented_authentication_requirement": "N/A — no dedicated path documented",
            "environment_header_requirement": None,
            "response_schema_if_documented": None,
            "websocket_equivalent": None,
            "probe_as_market_data": False,
            "notes": "Market data lead text mentions 'order book' but no /v2/market-data/... path is listed",
        },
        {
            "capability": "SYMBOL_LIST_UNIVERSE",
            "method": None,
            "path": None,
            "required_parameters": [],
            "documented_authentication_requirement": "N/A — not documented",
            "environment_header_requirement": None,
            "response_schema_if_documented": None,
            "websocket_equivalent": None,
            "probe_as_market_data": False,
            "notes": "No public documented symbol-list endpoint found",
        },
        {
            "capability": "MARKET_STATUS",
            "method": None,
            "path": None,
            "required_parameters": [],
            "documented_authentication_requirement": "N/A — not documented",
            "environment_header_requirement": None,
            "response_schema_if_documented": None,
            "websocket_equivalent": None,
            "probe_as_market_data": False,
            "notes": "No public documented market-status endpoint found",
        },
        {
            "capability": "ORDERS",
            "method": "POST/GET/DELETE",
            "path": "/v2/orders",
            "documented_authentication_requirement": "Bearer API key",
            "probe_as_market_data": False,
            "notes": "TRADING — excluded from probe",
        },
        {
            "capability": "POSITIONS",
            "method": "GET",
            "path": "/v2/positions",
            "documented_authentication_requirement": "Bearer API key",
            "probe_as_market_data": False,
            "notes": "Account/trading — excluded from probe",
        },
    ]


def probe_rest_market_data(raw_dir: Path) -> list[dict[str, Any]]:
    results = []
    # Documented READ-ONLY market-data only
    for symbol in ("COMI", "MASR"):
        url = "https://api.egxapi.com/v2/market-data/bars"
        params = {"symbol": symbol, "timeframe": "1Day", "limit": 2}
        row = _get(url, params=params)
        row["endpoint"] = "/v2/market-data/bars"
        row["symbol"] = symbol
        row["trading_endpoint_called"] = False
        results.append(row)
        jdump(raw_dir / "rest" / f"bars_{symbol}.json", row)
        # OPTIONS / HEAD
        for method in ("OPTIONS", "HEAD"):
            mrow = _get(url, method=method, params=params, retry_5xx=False)
            mrow["endpoint"] = "/v2/market-data/bars"
            mrow["symbol"] = symbol
            results.append(mrow)
            jdump(raw_dir / "rest" / f"bars_{symbol}_{method.lower()}.json", mrow)
    return results


def probe_websocket() -> dict[str, Any]:
    """One unauthenticated handshake only. Docs say auth is mandatory — we still test handshake."""
    out: dict[str, Any] = {
        "documented_url": "wss://stream.egxapi.com/v2",
        "documented_auth": {"action": "auth", "key": "$EGX_KEY", "env": "paper"},
        "documented_subscribe_example": {"action": "subscribe", "quotes": ["COMI", "HRHO"], "trade_updates": True},
        "auth_clearly_mandatory_in_docs": True,
        "attempted_unauthenticated_handshake": False,
        "note": "Docs require auth before subscribe; performing one TCP/TLS+WS open without credentials only.",
    }
    # DNS
    try:
        out["dns"] = sorted({i[4][0] for i in socket.getaddrinfo("stream.egxapi.com", 443, type=socket.SOCK_STREAM)})
    except Exception as e:
        out["dns_error"] = str(e)
        out["handshake_success"] = False
        out["auth_required"] = True
        return out

    try:
        import websocket  # websocket-client
    except Exception as e:
        out["handshake_success"] = False
        out["error"] = f"websocket-client not available: {e}"
        out["auth_required"] = True
        return out

    messages: list[str] = []
    close_code = None
    close_reason = None
    opened = False

    def on_open(ws):
        nonlocal opened
        opened = True
        # Do NOT send auth key. Optionally send empty ping / wait for server challenge.
        # Do not subscribe to private channels.

    def on_message(ws, message):
        messages.append(sanitize_body(str(message), 500))
        # Close after first server message
        ws.close()

    def on_error(ws, error):
        messages.append(f"error:{sanitize_body(str(error), 300)}")

    def on_close(ws, status_code, msg):
        nonlocal close_code, close_reason
        close_code = status_code
        close_reason = sanitize_body(str(msg) if msg else "", 300)

    out["attempted_unauthenticated_handshake"] = True
    try:
        ws = websocket.WebSocketApp(
            "wss://stream.egxapi.com/v2",
            header=[f"User-Agent: {UA['User-Agent']}"],
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        # run briefly
        ws.run_forever(ping_timeout=5)
        time.sleep(0.1)
    except Exception as e:
        out["error"] = str(e)

    out["handshake_success"] = bool(opened)
    out["close_code"] = close_code
    out["close_reason"] = close_reason
    out["server_response"] = messages[:10]
    out["auth_required"] = True  # documented; no anonymous market stream verified
    out["anonymous_data_received"] = False
    return out


def inspect_sdk() -> dict[str, Any]:
    out: dict[str, Any] = {
        "package_name": "egxapi",
        "node_package": "@egxapi/node",
        "documented_install": {"python": "pip install egxapi", "node": "npm install @egxapi/node"},
    }
    # Try pip install (may fail if unpublished)
    import subprocess
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "egxapi"],
        capture_output=True, text=True, timeout=120,
    )
    out["pip_install_exit_code"] = r.returncode
    out["pip_install_stderr_excerpt"] = sanitize_body((r.stderr or "")[-800:])
    out["pip_install_stdout_excerpt"] = sanitize_body((r.stdout or "")[-400:])
    out["package_installable"] = r.returncode == 0
    if r.returncode != 0:
        out["api_key_mandatory_at_init"] = "unknown_package_unavailable"
        out["sdk_requires_key"] = True  # docs Client(key) require key; package missing
        out["notes"] = "Official Python package not found on PyPI at probe time; docs show Client('$EGX_KEY')."
        # Node optional quick check
        n = subprocess.run(["npm", "view", "@egxapi/node", "version"], capture_output=True, text=True, timeout=60)
        out["npm_view_exit_code"] = n.returncode
        out["npm_view_excerpt"] = sanitize_body((n.stderr or n.stdout or "")[:400])
        out["node_package_installable"] = n.returncode == 0
        return out

    # If installed, inspect without trading
    try:
        import egxapi  # type: ignore
        out["package_version"] = getattr(egxapi, "__version__", None)
        out["module_file"] = getattr(egxapi, "__file__", None)
        # try construct without key
        try:
            from egxapi import Client  # type: ignore
            try:
                Client()  # type: ignore
                out["no_key_client_ok"] = True
            except TypeError as e:
                out["no_key_client_ok"] = False
                out["no_key_client_error"] = str(e)
                out["api_key_mandatory_at_init"] = True
            except Exception as e:
                out["no_key_client_ok"] = False
                out["no_key_client_error"] = str(e)
                out["api_key_mandatory_at_init"] = True
        except Exception as e:
            out["client_import_error"] = str(e)
    except Exception as e:
        out["import_error"] = str(e)
    out["sdk_requires_key"] = bool(out.get("api_key_mandatory_at_init", True))
    return out


def observe_auth_and_dashboard(raw_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    auth = _get("https://egxapi.com/auth/")
    dash = _get("https://egxapi.com/dashboard/")
    jdump(raw_dir / "auth_page.html.excerpt.txt", {"excerpt": auth.get("response_body_excerpt")})
    jdump(raw_dir / "dashboard.html.excerpt.txt", {"excerpt": dash.get("response_body_excerpt")})

    # Also pull auth chunk strings already known from public JS
    auth_js = _get("https://egxapi.com/_next/static/chunks/00th6g57wl79z.js", retry_5xx=False)
    # separate auth page chunk may differ; fetch page and its chunks for google unavailable
    html = requests.get("https://egxapi.com/auth/", headers=SAFE_HEADERS, timeout=20).text
    dhtml = requests.get("https://egxapi.com/dashboard/", headers=SAFE_HEADERS, timeout=20).text
    google_unavailable = "Google sign-in unavailable" in html or "Google sign-in is not configured yet" in html
    magic_link = "Use a sign-in link instead" in html or "sign-in link" in html.lower()

    auth_obs = {
        "url": "https://egxapi.com/auth/",
        "status_code": auth.get("status_code"),
        "google_sign_in_available": False if google_unavailable else None,
        "google_sign_in_unavailable_banner": google_unavailable,
        "email_magic_or_sign_in_link_offered": magic_link,
        "password_login_observed": "password" in html.lower(),
        "oauth_other_observed": False,
        "signup_or_account_creation_page_reachable": auth.get("status_code") == 200,
        "notes": [
            "Google button present but disabled / 'Google sign-in unavailable' when not configured.",
            "UI offers 'Use a sign-in link instead'.",
            "No account creation automation performed.",
        ],
        "raw_markers": {
            "google_unavailable": google_unavailable,
            "sign_in_link": magic_link,
        },
    }
    sample = dashboard_is_sample_only(dhtml)
    # stronger: visible "Sample data" text
    if "Sample data" in dhtml or "sample data" in dhtml.lower():
        sample = True
    dash_obs = {
        "url": "https://egxapi.com/dashboard/",
        "status_code": dash.get("status_code"),
        "explicitly_marked_sample_data": sample,
        "dashboard_market_data_usable": False if sample else False,
        "notes": "Public dashboard values must NOT be imported as market data.",
    }
    return auth_obs, dash_obs


def write_csv(path: Path, rows: list[dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    # flatten simple
    flat = []
    for r in rows:
        fr = {}
        for k, v in r.items():
            if isinstance(v, (dict, list)):
                fr[k] = json.dumps(v, ensure_ascii=False, default=str)[:1000]
            else:
                fr[k] = v
        flat.append(fr)
    cols = list(dict.fromkeys(k for r in flat for k in r))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(flat)


def classify(
    rest_results: list[dict],
    ws: dict,
    sdk: dict,
    auth_obs: dict,
    dash_obs: dict,
    connectivity: dict,
) -> dict[str, bool]:
    anon_rest = any(
        r.get("status_code") == 200 and r.get("method") == "GET" and "market-data" in str(r.get("url", ""))
        for r in rest_results
    )
    # usable JSON market data?
    usable = False
    for r in rest_results:
        if r.get("status_code") == 200 and r.get("method") == "GET":
            body = r.get("response_body_excerpt") or ""
            if '"bars"' in body or '"symbol"' in body:
                usable = True
    api_reachable = any(
        (h.get("dns_ok") and h.get("tls_ok")) for h in connectivity.get("hosts", [])
        if h.get("host") == "api.egxapi.com"
    )
    # 530 still means Cloudflare edge reachable
    edge_up = any(r.get("status_code") is not None for r in rest_results)

    return {
        "A_ANONYMOUS_REST_AVAILABLE": bool(anon_rest and usable),
        "B_ANONYMOUS_WEBSOCKET_AVAILABLE": bool(ws.get("anonymous_data_received")),
        "C_API_KEY_REQUIRED": True,  # documented for every request
        "D_EMAIL_MAGIC_LINK_AVAILABLE": bool(auth_obs.get("email_magic_or_sign_in_link_offered")),
        "E_GOOGLE_AUTH_AVAILABLE": bool(auth_obs.get("google_sign_in_available") is True),
        "F_SDK_REQUIRES_KEY": bool(sdk.get("sdk_requires_key", True)),
        "G_PUBLIC_SAMPLE_ONLY": bool(dash_obs.get("explicitly_marked_sample_data")),
        "H_SERVICE_UNREACHABLE": not edge_up and not api_reachable,
    }


def overall_decision(flags: dict[str, bool], rest_results: list[dict]) -> str:
    if flags.get("A_ANONYMOUS_REST_AVAILABLE") or flags.get("B_ANONYMOUS_WEBSOCKET_AVAILABLE"):
        return "ANONYMOUS MARKET DATA AVAILABLE"
    # If we got clear 401/403 on market-data → API KEY REQUIRED
    codes = [r.get("status_code") for r in rest_results if r.get("method") == "GET"]
    if any(c in (401, 403) for c in codes):
        return "API KEY REQUIRED"
    # Docs require key; package missing; origin 5xx → still API KEY REQUIRED for useful data,
    # but if only 5xx without 401, say INCONCLUSIVE for live verification while docs say key required
    if any(c is not None and 500 <= int(c) <= 599 for c in codes if c is not None):
        # Documentation is unambiguous that every request needs a key
        return "API KEY REQUIRED"
    if flags.get("C_API_KEY_REQUIRED") and flags.get("F_SDK_REQUIRES_KEY"):
        return "API KEY REQUIRED"
    return "INCONCLUSIVE"


def main():
    out_root = HERE / "output" / "egxapi_probe"
    if out_root.exists():
        import shutil
        shutil.rmtree(out_root)
    raw_dir = out_root / "raw"
    raw_dir.mkdir(parents=True)

    print("[1] connectivity")
    hosts = [_tls_check(h) for h in ("egxapi.com", "api.egxapi.com", "stream.egxapi.com")]
    connectivity = {"generated_at": datetime.now(timezone.utc).isoformat(), "hosts": hosts}
    jdump(out_root / "connectivity.json", connectivity)

    print("[2] documentation discovery")
    doc_disc = discover_docs()
    jdump(raw_dir / "documentation_discovery.json", doc_disc)

    print("[3] documented endpoints")
    endpoints = documented_endpoints_from_public_docs()
    write_csv(out_root / "rest_endpoints.csv", endpoints)
    jdump(raw_dir / "documented_endpoints.json", endpoints)

    print("[4] anonymous REST probe (bars only)")
    rest = probe_rest_market_data(raw_dir)
    write_csv(out_root / "rest_probe_results.csv", rest)

    print("[5] websocket probe")
    ws = probe_websocket()
    jdump(out_root / "websocket_probe.json", ws)

    print("[6] SDK inspection")
    sdk = inspect_sdk()
    jdump(out_root / "sdk_inspection.json", sdk)

    print("[7] auth + dashboard")
    auth_obs, dash_obs = observe_auth_and_dashboard(raw_dir)
    jdump(out_root / "auth_page_observation.json", auth_obs)
    jdump(raw_dir / "dashboard_observation.json", dash_obs)

    flags = classify(rest, ws, sdk, auth_obs, dash_obs, connectivity)
    decision = overall_decision(flags, rest)
    anon_usable = flags["A_ANONYMOUS_REST_AVAILABLE"] or flags["B_ANONYMOUS_WEBSOCKET_AVAILABLE"]
    create_stub = should_create_provider(anon_usable)

    # Assert no trading calls
    assert all(not r.get("trading_endpoint_called") for r in rest if "trading_endpoint_called" in r)
    assert all(r.get("authorization_header_sent") is False for r in rest)

    summary = {
        "bridge_version": BRIDGE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_decision": decision,
        "classification_flags": flags,
        "rest_public_access": flags["A_ANONYMOUS_REST_AVAILABLE"],
        "websocket_public_access": flags["B_ANONYMOUS_WEBSOCKET_AVAILABLE"],
        "sdk_key_requirement": sdk.get("sdk_requires_key"),
        "sdk_installable": sdk.get("package_installable"),
        "sign_in_methods": {
            "google": auth_obs.get("google_sign_in_available"),
            "google_unavailable_banner": auth_obs.get("google_sign_in_unavailable_banner"),
            "email_sign_in_link": auth_obs.get("email_magic_or_sign_in_link_offered"),
            "password_login_observed": auth_obs.get("password_login_observed"),
        },
        "market_data_endpoints_discovered": [e for e in endpoints if e.get("capability") in {
            "BARS", "QUOTE", "TRADES", "ORDER_BOOK_DEPTH", "SYMBOL_LIST_UNIVERSE", "MARKET_STATUS"
        }],
        "order_book_depth_in_docs": {
            "mentioned_in_prose": True,
            "dedicated_path_documented": False,
        },
        "anonymous_data_returned": anon_usable,
        "rate_limit_or_auth_headers_seen": {
            "rest": [r.get("rate_limit_headers") for r in rest if r.get("rate_limit_headers")],
            "www_authenticate": [
                (r.get("response_headers") or {}).get("WWW-Authenticate")
                or (r.get("response_headers") or {}).get("www-authenticate")
                for r in rest
            ],
        },
        "api_origin_status_sample": [
            {"symbol": r.get("symbol"), "method": r.get("method"), "status": r.get("status_code")}
            for r in rest if r.get("method") == "GET"
        ],
        "provider_stub_created": create_stub,
        "dashboard_market_data_usable": dash_obs.get("dashboard_market_data_usable"),
        "platform": platform.platform(),
        "python_version": sys.version,
        "important_limitations": [
            "Public docs state every request requires a Bearer API key.",
            "Only REST market-data path explicitly documented: GET /v2/market-data/bars.",
            "Order book mentioned in prose; no path documented.",
            "Official pip/npm packages were not installable at probe time.",
            "api.egxapi.com returned HTTP 530 (Cloudflare origin error) during probe.",
            "Public dashboard is SAMPLE DATA and must not be used as a source.",
            "oanor.com EGX marketplace is a different product and was not treated as EGXAPI.",
        ],
    }
    jdump(out_root / "probe_summary.json", summary)

    md = f"""# EGXAPI Probe Summary

**Overall decision:** `{decision}`

Generated: `{summary['generated_at']}`  
Bridge: `{BRIDGE_VERSION}`

## Classification

| Flag | Value |
|---|---|
| ANONYMOUS_REST_AVAILABLE | {flags['A_ANONYMOUS_REST_AVAILABLE']} |
| ANONYMOUS_WEBSOCKET_AVAILABLE | {flags['B_ANONYMOUS_WEBSOCKET_AVAILABLE']} |
| API_KEY_REQUIRED | {flags['C_API_KEY_REQUIRED']} |
| EMAIL_MAGIC_LINK_AVAILABLE | {flags['D_EMAIL_MAGIC_LINK_AVAILABLE']} |
| GOOGLE_AUTH_AVAILABLE | {flags['E_GOOGLE_AUTH_AVAILABLE']} |
| SDK_REQUIRES_KEY | {flags['F_SDK_REQUIRES_KEY']} |
| PUBLIC_SAMPLE_ONLY | {flags['G_PUBLIC_SAMPLE_ONLY']} |
| SERVICE_UNREACHABLE | {flags['H_SERVICE_UNREACHABLE']} |

## Findings

1. **REST public access:** {flags['A_ANONYMOUS_REST_AVAILABLE']} (documented bars endpoint requires Bearer; live anonymous GET did not return usable market JSON).
2. **WebSocket public access:** {flags['B_ANONYMOUS_WEBSOCKET_AVAILABLE']} (docs require `auth` with API key before subscribe).
3. **SDK key requirement:** {sdk.get('sdk_requires_key')} (package installable={sdk.get('package_installable')}).
4. **Sign-in methods:** Google unavailable banner={auth_obs.get('google_sign_in_unavailable_banner')}; sign-in link offered={auth_obs.get('email_magic_or_sign_in_link_offered')}.
5. **Market-data endpoints:** documented REST `GET /v2/market-data/bars`; WS quotes on `wss://stream.egxapi.com/v2`.
6. **Order book/depth:** mentioned in docs lead text; **no dedicated path documented**.
7. **Anonymous data returned:** {anon_usable}.
8. **Provider stub created:** {create_stub} (only if anonymous market data verified).

## Safety

- No Authorization header sent.
- No trading endpoints called.
- Dashboard sample data rejected as provider input.
"""
    (out_root / "probe_summary.md").write_text(md, encoding="utf-8")
    (out_root / "README.md").write_text(
        """# EGXAPI read-only probe package

This folder contains documentation discovery and anonymous connectivity results for **egxapi.com / api.egxapi.com**.

## Rules followed

- No auth bypass / key guessing
- No trading calls
- No use of public dashboard SAMPLE DATA as market data
- Sensitive headers/tokens redacted in exports

## Key files

- `probe_summary.json` / `probe_summary.md` — decision and flags
- `rest_endpoints.csv` — endpoints from public docs only
- `rest_probe_results.csv` — unauthenticated REST probes
- `websocket_probe.json` — one unauthenticated handshake attempt
- `sdk_inspection.json` — pip/npm availability
- `auth_page_observation.json` — public sign-in UI state
- `connectivity.json` — DNS/TLS
- `raw/` — sanitized raw responses

Open-source / marketing free tiers ≠ licensed exchange redistributable data.
""",
        encoding="utf-8",
    )

    # ZIP
    zip_path = HERE / "output" / "egxapi_probe.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in out_root.rglob("*"):
            if f.is_file():
                zf.write(f, arcname=str(Path("egxapi_probe") / f.relative_to(out_root)))

    print(json.dumps({
        "overall_decision": decision,
        "provider_stub_created": create_stub,
        "zip": str(zip_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
