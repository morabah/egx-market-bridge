from __future__ import annotations

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from egxbridge.semantics import (
    normalize_timestamp,
    volumes_comparable,
    session_date_cairo,
    is_latest_completed_session,
    previous_egx_session_date,
    BAR_VOLUME,
    DAILY_FINAL_VOLUME,
    SESSION_CUMULATIVE_VOLUME,
    CANDLE_CLOSE,
    DAILY_CLOSE,
    LIVE_QUOTE,
)
from egxbridge.conflicts import select_observation
from egxbridge.quality import score_symbol, compute_execution_grade
from egxbridge.providers.base import utc_now_iso


def test_bar_volume_vs_daily_volume_not_conflict():
    now = utc_now_iso()
    cands = [
        {
            "provider": "tradingview",
            "value": 852233.0,
            "volume_semantics": BAR_VOLUME,
            "interval": "5m",
            "session_date": "2026-09-03",
            "provider_timestamp": "2026-09-03T11:25:00+00:00",
            "freshness_seconds": 100,
        },
        {
            "provider": "yahoo",
            "value": 16712055.0,
            "volume_semantics": DAILY_FINAL_VOLUME,
            "interval": "1d",
            "session_date": "2026-09-03",
            "provider_timestamp": "2026-09-02T21:00:00+00:00",
            "freshness_seconds": 1000,
        },
    ]
    assert not volumes_comparable(cands[0], cands[1])
    sel = select_observation(
        cands, priority=["tradingview", "yahoo"], created_at=now, field="volume", symbol="MASR"
    )
    assert sel.conflict is None
    assert sel.skipped_incomparable
    assert sel.selected_provider == "tradingview"


def test_same_session_cumulative_volumes_may_conflict():
    now = utc_now_iso()
    cands = [
        {
            "provider": "tradingview",
            "value": 12.4e6,
            "volume_semantics": SESSION_CUMULATIVE_VOLUME,
            "session_date": "2026-09-03",
            "provider_timestamp": "2026-09-03T11:20:00+00:00",
            "freshness_seconds": 10,
        },
        {
            "provider": "yahoo",
            "value": 10.8e6,
            "volume_semantics": SESSION_CUMULATIVE_VOLUME,
            "session_date": "2026-09-03",
            "provider_timestamp": "2026-09-03T11:05:00+00:00",
            "freshness_seconds": 900,
        },
    ]
    assert volumes_comparable(cands[0], cands[1])
    sel = select_observation(
        cands, priority=["tradingview", "yahoo"], created_at=now, field="volume", symbol="MASR"
    )
    assert sel.conflict is not None
    assert sel.selected_value == 12.4e6


def test_naive_timestamps_not_automatically_utc():
    naive = datetime(2026, 9, 3, 14, 25, 0)  # no tz
    bundle = normalize_timestamp(naive, timestamp_semantics="BAR_OPEN")
    assert bundle.normalized_utc_timestamp is None
    assert bundle.naive_treated_as_utc is False


def test_cairo_utc_normalization_for_tv_host_local():
    # Simulate tvDatafeed naive host-local (Cairo UTC+3) bar open at 14:25
    naive = datetime(2026, 9, 3, 14, 25, 0)
    bundle = normalize_timestamp(
        naive, provider_timezone_if_known="Africa/Cairo", timestamp_semantics="BAR_OPEN"
    )
    assert bundle.normalized_utc_timestamp is not None
    assert bundle.normalized_utc_timestamp.startswith("2026-09-03T11:25:00")
    assert "14:25" in (bundle.normalized_cairo_timestamp or "")
    assert bundle.provider_timezone_if_known == "Africa/Cairo"


def test_candle_price_not_live_quote():
    q = score_symbol(
        symbol="MASR",
        freshness_class="STALE_EXPECTED",
        price_observation_type=CANDLE_CLOSE,
        has_price=True,
        has_volume=True,
        has_daily=True,
        has_intraday=True,
        timestamp_known=True,
        timestamp_reliable=True,
        latest_completed_session=True,
    )
    assert q.execution_grade == "NO"
    assert "execution_grade_price_observation" in q.missing_execution_fields or any(
        "price" in m for m in q.missing_execution_fields
    )


def test_execution_grade_fails_without_current_session_fields():
    grade, missing = compute_execution_grade(
        session_open=False,
        price_observation_type=DAILY_CLOSE,
        freshness_class="STALE_EXPECTED",
        has_current_session_price=False,
        has_current_session_volume=False,
        timestamp_reliable=True,
    )
    assert grade == "NO"
    assert "egx_session_open" in missing


def test_weekend_latest_completed_session_research_usable():
    # Saturday capture, Thursday session observation
    saturday = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)
    assert previous_egx_session_date(saturday) == "2026-09-03"
    assert is_latest_completed_session("2026-09-03", saturday)
    q = score_symbol(
        symbol="MASR",
        freshness_class="STALE_EXPECTED",
        has_price=True,
        has_volume=True,
        has_daily=True,
        has_intraday=True,
        timestamp_known=True,
        timestamp_reliable=True,
        latest_completed_session=True,
        price_observation_type=CANDLE_CLOSE,
    )
    # Research freshness boosted vs raw STALE_EXPECTED(30)
    assert q.components["freshness"] >= 72.0
    assert q.research_data_quality > 50
    assert q.execution_grade == "NO"
    assert q.latest_completed_session is True


def test_yahoo_daily_session_date_from_cairo_aware():
    ts = "2026-09-03T00:00:00+03:00"
    assert session_date_cairo(ts) == "2026-09-03"


def test_daily_bars_same_session_not_ranked_by_wall_clock():
    """Yahoo 00:00 vs TV 10:00 same session → priority wins, not wall-clock."""
    now = utc_now_iso()
    # Intentionally give Yahoo a "fresher" huge age advantage if wall-clock were used
    # (00:00 is older). TV has later wall-clock label but lower priority than yahoo
    # when yahoo is listed first.
    cands = [
        {
            "provider": "yahoo",
            "value": 7.98,
            "timestamp_semantics": "DAILY_BAR",
            "price_observation_type": "DAILY_CLOSE",
            "volume_semantics": "DAILY_FINAL_VOLUME",
            "session_date": "2026-09-03",
            "effective_session_date": "2026-09-03",
            "provider_raw_timestamp": "2026-09-03T00:00:00+03:00",
            "freshness_seconds": 200000,  # looks staler by wall-clock
        },
        {
            "provider": "tradingview",
            "value": 7.95,
            "timestamp_semantics": "DAILY_BAR",
            "price_observation_type": "DAILY_CLOSE",
            "volume_semantics": "DAILY_FINAL_VOLUME",
            "session_date": "2026-09-03",
            "effective_session_date": "2026-09-03",
            "provider_raw_timestamp": "2026-09-03T10:00:00+03:00",
            "freshness_seconds": 100,  # looks much fresher by wall-clock
        },
    ]
    # yahoo-first priority: must select yahoo despite "staler" wall-clock
    sel = select_observation(
        cands, priority=["yahoo", "tradingview"], created_at=now, field="last", symbol="MASR"
    )
    assert sel.selected_provider == "yahoo"
    assert sel.selected_value == 7.98
    assert "wall-clock" in sel.reason
    assert sel.conflict is not None  # material price disagreement preserved
    assert sel.conflict.value_a == 7.98
    assert sel.conflict.value_b == 7.95


def test_daily_final_volume_conflict_visible_same_session():
    now = utc_now_iso()
    cands = [
        {
            "provider": "tradingview",
            "value": 149448471.0,
            "volume_semantics": "DAILY_FINAL_VOLUME",
            "timestamp_semantics": "DAILY_BAR",
            "session_date": "2026-09-03",
            "effective_session_date": "2026-09-03",
            "provider_raw_timestamp": "2026-09-03T10:00:00+03:00",
            "freshness_seconds": 50,
        },
        {
            "provider": "yahoo",
            "value": 140001947.0,
            "volume_semantics": "DAILY_FINAL_VOLUME",
            "timestamp_semantics": "DAILY_BAR",
            "session_date": "2026-09-03",
            "effective_session_date": "2026-09-03",
            "provider_raw_timestamp": "2026-09-03T00:00:00+03:00",
            "freshness_seconds": 200000,
        },
    ]
    sel = select_observation(
        cands,
        priority=["yahoo", "tradingview"],
        created_at=now,
        field="volume",
        symbol="LUTS",
        require_comparable_volume=True,
    )
    assert sel.selected_provider == "yahoo"  # priority, not TV wall-clock
    assert sel.conflict is not None
    assert sel.conflict.session_date == "2026-09-03"
    assert "wall-clock" in sel.reason


def test_intraday_bar_volume_still_uses_timestamp_freshness():
    now = utc_now_iso()
    # Equal priority slot: both unknown to priority list → freshness decides
    cands = [
        {
            "provider": "tradingview",
            "value": 100.0,
            "volume_semantics": "BAR_VOLUME",
            "timestamp_semantics": "BAR_OPEN",
            "interval": "5m",
            "session_date": "2026-09-03",
            "freshness_seconds": 500,
        },
        {
            "provider": "alt_tv",
            "value": 110.0,
            "volume_semantics": "BAR_VOLUME",
            "timestamp_semantics": "BAR_OPEN",
            "interval": "5m",
            "session_date": "2026-09-03",
            "freshness_seconds": 10,
        },
    ]
    sel = select_observation(
        cands, priority=["nosuch"], created_at=now, field="volume", symbol="X", require_comparable_volume=True
    )
    # Both prio=999; fresher (10s) wins
    assert sel.selected_provider == "alt_tv"
    assert sel.selected_value == 110.0
