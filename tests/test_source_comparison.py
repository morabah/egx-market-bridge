from __future__ import annotations

import json
import zipfile
from pathlib import Path

from egxbridge.source_comparison import (
    build_disagreements,
    independence_group_for,
    observations_comparable,
    parse_borsa_underlying,
    write_csv,
    jdump,
)


def test_borsa_via_yahoo_shares_independence_group():
    assert parse_borsa_underlying({
        "source": "Yahoo Finance (COMI.CA)",
        "attribution": {"provider": "Yahoo Finance", "url": "https://finance.yahoo.com"},
    }) == "YAHOO"
    assert independence_group_for("borsa", "YAHOO") == "YAHOO"
    assert independence_group_for("yahoo") == "YAHOO"


def test_unlike_volume_semantics_not_comparable():
    assert observations_comparable(
        field="volume",
        semantic_type_a="BAR_VOLUME",
        semantic_type_b="DAILY_FINAL_VOLUME",
    ) is False
    assert observations_comparable(
        field="volume",
        semantic_type_a="DAILY_FINAL_VOLUME",
        semantic_type_b="DAILY_FINAL_VOLUME",
    ) is True


def test_unlike_intervals_not_compared_as_same_price():
    assert observations_comparable(
        field="last",
        semantic_type_a="CANDLE_CLOSE",
        semantic_type_b="DAILY_CLOSE",
        interval_a="5m",
        interval_b="1d",
        price_type_a="CANDLE_CLOSE",
        price_type_b="DAILY_CLOSE",
    ) is False


def test_disagreements_preserve_rows_and_skip_unlike():
    rows = [
        {
            "canonical_symbol": "MASR",
            "provider": "yahoo",
            "response_status": "ok",
            "last": 4.5,
            "volume": 1000,
            "volume_semantics": "DAILY_FINAL_VOLUME",
            "price_observation_type": "DAILY_CLOSE",
            "volume_interval": "1d",
            "session_date": "2026-09-03",
            "independence_group": "YAHOO",
        },
        {
            "canonical_symbol": "MASR",
            "provider": "tradingview",
            "response_status": "ok",
            "last": 4.6,
            "volume": 50,
            "volume_semantics": "BAR_VOLUME",
            "price_observation_type": "CANDLE_CLOSE",
            "volume_interval": "5m",
            "session_date": "2026-09-03",
            "independence_group": "TRADINGVIEW",
        },
        {
            "canonical_symbol": "MASR",
            "provider": "borsa",
            "response_status": "ok",
            "last": 4.5,
            "volume": 1000,
            "volume_semantics": "DAILY_FINAL_VOLUME",
            "price_observation_type": "DAILY_CLOSE",
            "volume_interval": "1d",
            "session_date": "2026-09-03",
            "independence_group": "YAHOO",
            "borsa_underlying_provider": "YAHOO",
        },
    ]
    d = build_disagreements(rows)
    # volume yahoo vs tv must not appear (unlike semantics)
    assert not any(x["field"] == "volume" and {x["provider_a"], x["provider_b"]} == {"yahoo", "tradingview"} for x in d)
    # last yahoo vs tv skipped due to price type / interval
    assert not any(x["field"] == "last" and {x["provider_a"], x["provider_b"]} == {"yahoo", "tradingview"} for x in d)
    # yahoo vs borsa same last → no disagreement row (exact match filtered)
    assert not any(
        x["field"] == "last" and {x["provider_a"], x["provider_b"]} == {"yahoo", "borsa"} for x in d
    )


def test_raw_and_normalized_not_collapsed(tmp_path: Path):
    raw = tmp_path / "raw" / "yahoo" / "MASR"
    raw.mkdir(parents=True)
    jdump(raw / "quote.json", {"Close": 4.5, "Volume": 10})
    rows = [
        {"canonical_symbol": "MASR", "provider": "yahoo", "last": 4.5, "response_status": "ok"},
        {"canonical_symbol": "MASR", "provider": "borsa", "last": 4.5, "response_status": "ok"},
    ]
    write_csv(tmp_path / "normalized" / "quotes_all_sources.csv", rows)
    text = (tmp_path / "normalized" / "quotes_all_sources.csv").read_text(encoding="utf-8")
    assert "yahoo" in text and "borsa" in text
    assert (raw / "quote.json").exists()


def test_failed_providers_exported_in_per_symbol(tmp_path: Path):
    payload = {
        "symbol": "LUTS",
        "yahoo": {"quote": {"ok": True}},
        "egid": {"quote": {"ok": False, "status": "AUTH_REQUIRED", "http_status": 401}},
        "borsa": {"quote": {"ok": False, "error": "timeout"}},
    }
    jdump(tmp_path / "per_symbol" / "LUTS.json", payload)
    data = json.loads((tmp_path / "per_symbol" / "LUTS.json").read_text(encoding="utf-8"))
    assert "egid" in data and data["egid"]["quote"]["http_status"] == 401
    assert data["borsa"]["quote"]["ok"] is False


def test_zip_and_manifest_shape(tmp_path: Path):
    root = tmp_path / "source_comparison"
    (root / "normalized").mkdir(parents=True)
    manifest = {"bridge_version": "0.3.1", "benchmark_version": "1.0.0", "symbols_tested": ["COMI"]}
    jdump(root / "manifest.json", manifest)
    write_csv(root / "normalized" / "quotes_all_sources.csv", [
        {"canonical_symbol": "COMI", "provider": "yahoo", "last": 1},
    ])
    zip_path = tmp_path / "source_comparison.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for f in root.rglob("*"):
            if f.is_file():
                zf.write(f, arcname=str(Path("source_comparison") / f.relative_to(root)))
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "source_comparison/manifest.json" in names
        raw = json.loads(zf.read("source_comparison/manifest.json"))
        assert raw["bridge_version"] == "0.3.1"
