from __future__ import annotations

from egxbridge.universe import (
    EQUITY, INDEX, FUND,
    classify_security_type,
    UniverseRecord,
    build_canonical_universe,
    assess_universe_coverage,
)
from egxbridge.analysis.explorer.coverage import classify_explorer_coverage


def test_index_excluded_from_stock_universe():
    assert classify_security_type("EGX30") == INDEX
    assert classify_security_type("EGX70") == INDEX
    assert classify_security_type("EGX100") == INDEX
    built = build_canonical_universe(explicit=["EGX30", "COMI", "KASABF"])
    recs = built["records_by_symbol"]
    assert recs["EGX30"].security_type == INDEX
    assert recs["EGX30"].is_tradable_candidate is False
    assessed = assess_universe_coverage(built, db=None)
    assert assessed["status_by_symbol"]["EGX30"]["exclusion_reason"].startswith("EXCLUDED_INDEX")
    assert "EGX30" not in assessed["SCANNER_ELIGIBLE_SYMBOLS"]
    assert "COMI" in assessed["equity_symbols"]


def test_fund_recognized_not_ordinary_equity():
    assert classify_security_type("KASABF") == FUND
    rec = UniverseRecord(canonical_symbol="KASABF", security_type=FUND)
    assert rec.security_type == FUND
    assert rec.is_tradable_candidate is False


def test_ordinary_equity_included():
    rec = UniverseRecord(canonical_symbol="COMI")
    assert rec.security_type == EQUITY
    assert rec.is_tradable_candidate is True
    assert rec.provider_alias_yahoo == "COMI.CA"
    assert rec.provider_alias_tradingview == "EGX:COMI"


def test_unmapped_ticker_preserved_with_reason():
    rec = UniverseRecord(canonical_symbol="ZZZX", mapped=False, security_type=EQUITY)
    built = {
        "records": [rec],
        "UNIVERSE_TOTAL": 1,
        "EQUITY_UNIVERSE_TOTAL": 1,
        "security_type_counts": {EQUITY: 1},
        "all_symbols": ["ZZZX"],
        "universe_source": "test",
    }
    assessed = assess_universe_coverage(built, db=None)
    assert "ZZZX" in assessed["UNMAPPED_SYMBOLS"]
    assert assessed["exclusion_reasons"]["ZZZX"] == "NO_MAPPING"
    assert "ZZZX" not in assessed["SCANNER_ELIGIBLE_SYMBOLS"]


def test_reference_universe_not_hardcoded_ten():
    uni = build_canonical_universe()
    assert uni["UNIVERSE_TOTAL"] >= 100
    assert uni["EQUITY_UNIVERSE_TOTAL"] >= 100
    counts = uni["security_type_counts"]
    assert counts.get(INDEX, 0) >= 3
    assert counts.get(FUND, 0) >= 1


def test_coverage_4_of_139_is_insufficient_not_broad():
    cov = classify_explorer_coverage(
        equity_universe_total=139,
        mapped_symbols=139,
        daily_data_available=4,
        scanner_eligible=4,
    )
    assert cov["scanner_eligible_coverage_pct"] == round(100 * 4 / 139, 2)
    assert cov["EXPLORER_COVERAGE"] == "INSUFFICIENT"
    assert cov["selection_basis"] == "PARTIAL_UNIVERSE"
    assert cov["selection_bias_risk"] == "HIGH"
    assert cov["market_wide_confidence_allowed"] is False


def test_coverage_percentages_and_high_threshold():
    cov = classify_explorer_coverage(
        equity_universe_total=100,
        mapped_symbols=90,
        daily_data_available=85,
        scanner_eligible=82,
    )
    assert cov["mapped_coverage_pct"] == 90.0
    assert cov["daily_data_coverage_pct"] == 85.0
    assert cov["scanner_eligible_coverage_pct"] == 82.0
    assert cov["EXPLORER_COVERAGE"] == "HIGH"
    assert cov["selection_basis"] == "BROAD_UNIVERSE"
    assert cov["market_wide_confidence_allowed"] is True
