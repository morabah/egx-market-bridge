from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json
import tempfile
import pandas as pd


def jdump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        temporary = Path(tmp.name)
        try:
            tmp.write(payload)
            tmp.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def rows_to_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = []
    for r in rows:
        clean.append({k: v for k, v in r.items() if k != "raw"})
    pd.DataFrame(clean).to_csv(path, index=False)


def append_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    clean = [{k: v for k, v in r.items() if k != "raw"} for r in rows]
    df = pd.DataFrame(clean)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, mode="a", header=not path.exists(), index=False)


def write_handoff(outdir: Path, payload: dict):
    jdump(outdir / "chatgpt_handoff.json", payload)
    lines = [
        "# EGX MARKET DATA HANDOFF",
        "",
        f"Generated: {payload.get('generated_at')}",
        f"Version: {payload.get('version', '0.3')}",
        f"Provider mode: {payload.get('provider_mode')}",
        f"Status: {payload.get('status')}",
        ""
    ]
    for s in payload.get("symbols", []):
        q = s.get("quote", {}) or {}
        lines += [
            f"## {s.get('symbol')}",
            f"- Last: {q.get('last') or s.get('price')} (source: {s.get('price_source') or q.get('provider')})",
            f"- Freshness: {s.get('freshness') or q.get('freshness_class')}",
            f"- Bid / Ask: {q.get('bid')} / {q.get('ask')}",
            f"- Bid qty / Ask qty: {q.get('bid_qty')} / {q.get('ask_qty')}",
            f"- Volume: {q.get('volume') or s.get('volume')} (source: {s.get('volume_source')})",
            f"- Trades: {q.get('trades')}",
            f"- Turnover: {q.get('turnover')}",
            f"- Spread bps: {s.get('spread_bps')}",
            f"- Top-depth imbalance: {s.get('depth_imbalance')}",
            f"- Research DQ: {s.get('research_data_quality')} | Execution DQ: {s.get('execution_data_quality')}",
            f"- Missing execution fields: {', '.join(s.get('missing_execution_fields') or []) or 'n/a'}",
            f"- Data warnings: {', '.join(s.get('warnings', [])) if s.get('warnings') else 'none'}",
            ""
        ]
    (outdir / "chatgpt_handoff.md").write_text("\n".join(lines), encoding="utf-8")


def write_scanner_handoff(outdir: Path, payload: dict):
    jdump(outdir / "scanner_handoff.json", payload)


def now_iso():
    return datetime.now(timezone.utc).isoformat()
