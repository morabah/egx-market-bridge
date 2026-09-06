"""Chronological forward-validation evidence. No recommendations or automatic tuning.

Canonical identity and outcome arithmetic remain owned by schedule.identity/outcomes.
This module owns sample enrollment, immutable classifications and descriptive reports.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median, mean
from typing import Any
import json
import math

from egxbridge import __version__ as APP_VERSION
from egxbridge.analysis import SCORING_VERSION
from egxbridge.analysis.common.models import utc_now, content_hash
from egxbridge.analysis.funnel.schema import normalize_fields, finite_number, JUDGMENT_FIELDS, MISSING_VALUES
from egxbridge.analysis.schedule.session import CAIRO, parse_dt, PRE_OPEN_END
from egxbridge.analysis.schedule.outcomes import unique_trading_sessions, _session_key

HORIZONS = (1, 2, 5, 10, 20)
SAMPLE_ROLES = {"DISCOVERY", "FORWARD_VALIDATION", "HOLDOUT", "HINDSIGHT_DESCRIPTIVE", "DISCOVERY_FOR_NEW_RULE"}
POINT_IN_TIME_KINDS = {"CONTEMPORANEOUS", "RECONSTRUCTED_POINT_IN_TIME", "DISCOVERY_SAMPLE", "HINDSIGHT_DESCRIPTIVE"}
DEFAULT_CONFIG = {
    "serious_candidate_basis": "PRESCREEN_OR_FINAL_HANDOFF",
    "descriptive_below": 20, "review_eligible_at": 50, "minimum_group_n": 20,
    "false_negative_top_n": 20, "false_negative_top_fraction": None,
    "poor_return_10_pct": -3.0, "adverse_mae_pct": -8.0,
    "round_increment_mantissas": [1, 2, 5], "round_distance_pct": 1.0,
    "pullback_min_pct": 3.0, "pullback_max_pct": 8.0,
    "friction_model": {"friction_model_version": "1", "components_pct": {}, "friction_inputs_source": None},
}
RESPONSIBILITY_MATRIX = {
    "APP": ["OHLCV", "timestamps", "provenance", "market breadth", "returns", "RVOL", "SMA", "ATR", "RS with benchmark", "CLV", "canonical identity", "immutable T0", "whole eligible universe", "MFE/MAE", "friction arithmetic", "target/stop arithmetic", "descriptive group statistics", "false-negative audit"],
    "FUNNEL_LLM": sorted(JUDGMENT_FIELDS),
    "SCHEDULE_LLM": ["news/macro/tactical interpretation", "PROMOTE/DOWNGRADE", "Funnel routing"],
    "WEEKLY_LLM": ["validation interpretation", "later event review", "KEEP_RULE/INVESTIGATE_RULE/PROPOSE_CHANGE"],
    "USER": ["final capital decision", "external rule-change approval"],
    "DEVELOPER": ["implement explicitly approved versioned rules; new chronological sample"],
}


def _id(*parts: Any) -> str:
    return content_hash(json.dumps(parts, sort_keys=True, default=str))[:40]


def validation_run(store) -> dict | None:
    rows = store.validation_records("forward_test_runs")
    return rows[0] if rows else None


def start_validation(store, *, at: str | None = None, config: dict | None = None) -> dict:
    existing = validation_run(store)
    if existing:
        return existing
    # Production start is the actual enrollment clock; it cannot be backdated.
    started = utc_now() if store.environment == "PRODUCTION" else (at or utc_now())
    if parse_dt(started) is None:
        raise ValueError("Invalid forward-validation start")
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    if not 0 < cfg["descriptive_below"] < cfg["review_eligible_at"] or cfg["minimum_group_n"] < 1:
        raise ValueError("Invalid interpretation bands")
    if not isinstance(cfg["false_negative_top_n"], int) or cfg["false_negative_top_n"] < 1:
        raise ValueError("False-negative top N must be a positive integer")
    fraction = cfg.get("false_negative_top_fraction")
    if fraction is not None and (finite_number(fraction) is None or not 0 < fraction <= 1):
        raise ValueError("False-negative fraction must be greater than zero and at most one")
    if not 0 <= cfg["pullback_min_pct"] < cfg["pullback_max_pct"] < 100:
        raise ValueError("Invalid pullback magnitude range")
    if (not cfg["round_increment_mantissas"] or
            any(finite_number(v) is None or float(v) <= 0 for v in cfg["round_increment_mantissas"]) or
            finite_number(cfg["round_distance_pct"]) is None or cfg["round_distance_pct"] < 0):
        raise ValueError("Round increments must be positive and proximity nonnegative")
    costs = (cfg.get("friction_model") or {}).get("components_pct") or {}
    if any(k not in {"brokerage", "exchange_regulatory", "taxes", "spread", "slippage", "entry", "exit"}
           or not isinstance(v, (int, float)) or finite_number(v) is None or v < 0 for k, v in costs.items()):
        raise ValueError("Friction components must be known nonnegative finite percentage-point costs")
    run = {"FORWARD_VALIDATION_START": started, "status": "ACTIVE", "config": cfg,
           "application_version": APP_VERSION, "scoring_version": SCORING_VERSION,
           "default_sample_kind": "CONTEMPORANEOUS", "synthetic": store.environment != "PRODUCTION"}
    store.append_validation_record("forward_test_runs", "forward-v070", run)
    rules = {
        "scanner_score": (SCORING_VERSION, "Existing explorer.calibration definition, frozen; serious sample = configured prescreen or final handoff"),
        "pullback_rule": ("1", {"prior_uptrend": "close before peak > SMA20 > SMA50 at peak", "magnitude_pct": [cfg["pullback_min_pct"], cfg["pullback_max_pct"]], "support": "current low >= pre-pullback SMA20", "volume": "pullback average < prior impulse average when measurable", "reclaim": "current close > preceding session high"}),
        "breakout_volume_bins": ("1", {"bins": [1, 1.5, 2], "status": "INITIAL_ANALYSIS_BINS"}),
        "CLV": ("1", {"formula": "(2*close-high-low)/(high-low)", "bins": [-0.33, 0.33], "status": "HEURISTIC_INITIAL"}),
        "PLSS": ("2.8_initial", "Store supplied raw score, available max, evidence coverage and individual components; missing is not negative. HEURISTIC."),
        "round_numbers": ("1", {"mantissas": cfg["round_increment_mantissas"], "distance_pct": cfg["round_distance_pct"], "formula": "largest configured mantissa * 10^(floor(log10(price))-1) whose nearest anchor is within distance_pct"}),
    }
    for name, (version, definition) in rules.items():
        store.append_validation_record("rule_definitions", f"{name}:{version}", {
            "rule_name": name, "rule_version": version, "definition": definition,
            "effective_from": started, "effective_until": None, "status": "HEURISTIC_UNCALIBRATED",
            "origin": "INITIAL_V070" if name != "scanner_score" else "EXISTING_V051",
        })
    return validation_run(store)


def eligible_sample(row: dict, *, include_reconstructed: bool = False) -> bool:
    return (row.get("sample_role") == "FORWARD_VALIDATION" and
            (row.get("point_in_time_kind") == "CONTEMPORANEOUS" or
             (include_reconstructed and row.get("point_in_time_kind") == "RECONSTRUCTED_POINT_IN_TIME" and
              bool(row.get("reconstruction_provenance_verified")))) and
            row.get("enrolled_after_start") is True)


def round_encounters(price: float | None, cfg: dict) -> list[dict]:
    if price is None or price <= 0:
        return []
    scale = 10 ** (math.floor(math.log10(price)) - 1)
    mantissas = [float(v) for v in cfg["round_increment_mantissas"] if finite_number(v) and float(v) > 0]
    if not mantissas:
        return []
    for increment in sorted((m * scale for m in mantissas), reverse=True):
        level = round(price / increment) * increment
        distance = (price / level - 1) * 100 if level > 0 else None
        if distance is not None and abs(distance) <= cfg["round_distance_pct"]:
            return [{"round_level": round(level, 8), "distance_pct": round(distance, 6),
                     "round_increment": increment, "round_rule_version": "1", "interpretation": "OBSERVATIONAL_ONLY"}]
    return []


def local_evidence(candidate: dict, *, session: str, cutoff: str, cfg: dict, benchmark: list[dict] | None = None) -> dict:
    m = {**(candidate.get("metrics") or {}), **candidate}
    struct = candidate.get("structure") or {}
    bars = [b for b in unique_trading_sessions(candidate.get("candles") or []) if (_session_key(b) or "") <= session]
    last = bars[-1] if bars else {}
    def pick(*keys):
        return next((m[k] for k in keys if m.get(k) is not None), None)
    price = finite_number(pick("price_t0", "price_at_snapshot", "last_close", "latest_close"))
    if price is None:
        price = finite_number(last.get("close"))
    def trailing(n):
        if len(bars) <= n:
            return None
        past = finite_number(bars[-1-n].get("close"))
        return round((price / past - 1) * 100, 6) if price is not None and past and past > 0 else None
    hi, lo, close = [finite_number(last.get(k)) for k in ("high", "low", "close")]
    clv = (2 * close - hi - lo) / (hi - lo) if None not in (hi, lo, close) and hi > lo > 0 and lo <= close <= hi else None
    reference = finite_number(pick("breakout_reference")) or finite_number(struct.get("breakout_reference"))
    if reference is None and len(bars) >= 21:
        highs = [finite_number(b.get("high")) for b in bars[-21:-1]]
        if all(v is not None and v > 0 for v in highs):
            reference = max(highs)
    out = {
        "price_t0": price, "price_basis": pick("price_basis", "price_observation_type") or "OFFICIAL_CLOSE",
        "price_timestamp": pick("price_timestamp") or _session_key(last) or session,
        "price_integrity": pick("price_integrity") or "DAILY_REFERENCE_NOT_EXECUTION_PRICE",
        "daily_return": pick("daily_return_pct", "daily_return"),
        "volume": finite_number(last.get("volume")), "trading_value": pick("trading_value"),
        "volume_ratio_20d": pick("rvol_20", "RVOL20"), "value_ratio_20d": pick("value_ratio_20d"),
        "distance_20d_high": pick("dist_from_20d_high_pct", "distance_20d_high"),
        "distance_60d_high": pick("dist_from_60d_high_pct", "distance_60d_high"),
        "sma20_relationship": pick("above_or_below_SMA20") or struct.get("above_or_below_SMA20"),
        "sma50_relationship": pick("above_or_below_SMA50") or struct.get("above_or_below_SMA50"),
        "ATR": pick("atr_14"), "realized_volatility": pick("realized_vol_20d_ann_pct"),
        "breakout_state": pick("breakout_20d", "breakout_flag_20d"),
        "breakout_reference": reference, "breakout_level": reference,
        "breakout_distance": (price / reference - 1) * 100 if price and reference else None,
        "breakout_close_acceptance": price >= reference if price and reference else None,
        "breakout_session": session if price and reference and price >= reference else None,
        "breakout_acceptance_local_evidence": "CLOSE_VS_PRIOR_HIGH_ONLY", "CLV": clv,
        "technical_history_integrity": pick("TECHNICAL_HISTORY_INTEGRITY", "technical_history_integrity"),
        "forward_setup_quality": pick("FORWARD_SETUP_QUALITY", "forward_setup_quality"),
        "move_already_realized": pick("MOVE_ALREADY_REALIZED", "move_already_realized"),
        "candidate_lane": pick("candidate_lane"), "candidate_families": pick("candidate_families") or [],
        "candidate_score_calibrated": pick("candidate_score_calibrated"), "forward_setup_score": pick("forward_setup_score"),
        "source_cutoff_timestamp": cutoff, "market_data_cutoff": session,
        "funnel_data_cutoff": ((candidate.get("funnel_ctx") or candidate.get("funnel_context") or {}).get("structured_provenance") or {}).get("source_cutoff"), "schedule_data_cutoff": None,
        "security_id": pick("security_id"), "sector": pick("sector") or "UNKNOWN",
        "market_cap_bucket": pick("market_cap_bucket") or "UNKNOWN",
        "market_tape_regime_local_input": pick("market_tape_regime_local_input") or "NOT_RELIABLE",
        "market_liquidity_regime": pick("market_liquidity_regime") or "NOT_RELIABLE",
        "data_quality_and_provider_evidence": candidate.get("market_source_evidence") or {},
        "provider_freshness": (candidate.get("market_source_evidence") or {}).get("freshness_class") or last.get("freshness_class") or "NOT_AVAILABLE",
        "source_provenance": pick("providers_used", "source_provenance") or list({str(b.get("provider")) for b in bars if b.get("provider")}),
        "scoring_version": SCORING_VERSION, "score_status": "HEURISTIC_UNCALIBRATED",
        "scanner_metrics": candidate.get("metrics") or {},
        "scanner_components": {k: candidate.get(k) for k in ("breakdown", "forward_setup_components", "structure", "history_integrity", "move_realized_reasons", "candidate_warnings")},
        "entry_executable_data_available": pick("entry_executable_data_available") is True,
        "fillability_data_available": pick("fillability_data_available") is True,
        "bid_ask_available": pick("bid_ask_available") is True, "depth_available": pick("depth_available") is True,
        "trade_tape_available": pick("trade_tape_available") is True,
        "catalyst_state": "NOT_ANALYZED", "psychological_levels": [],
        "target_price_t0": finite_number(pick("target_price_t0")) if pick("target_source") else None,
        "stop_or_invalidation_t0": finite_number(pick("stop_or_invalidation_t0")) if pick("stop_source") else None,
        "target_source": pick("target_source"), "stop_source": pick("stop_source"),
        "PLSS_status": "HEURISTIC", "round_number_encounters": round_encounters(price, cfg),
        "friction_model": cfg["friction_model"], "last_ohlcv": last,
    }
    for h in (5, 10, 20, 60):
        out[f"return_{h}d_trailing"] = trailing(h)
    bmap = {_session_key(b): finite_number(b.get("close")) for b in (benchmark or []) if (_session_key(b) or "") <= session}
    for h in (5, 20, 60):
        out[f"RS{h}"] = pick(f"RS{h}")
        if out[f"RS{h}"] is None and len(bars) > h:
            end, start = bmap.get(_session_key(bars[-1])), bmap.get(_session_key(bars[-1-h]))
            stock_return = trailing(h)
            if end and start and stock_return is not None:
                out[f"RS{h}"] = stock_return - (end / start - 1) * 100
    out.update(pullback_evidence(bars, cfg))
    return out


def pullback_evidence(bars: list[dict], cfg: dict) -> dict:
    result = {"pullback_rule_version": "1", "pullback_pct": None, "support_distance": None,
              "volume_contraction_ratio": None, "prior_uptrend": None, "support_not_broken": None,
              "reclaim_state": "NOT_AVAILABLE", "pullback_mechanical_match": None}
    if len(bars) < 61:
        return result
    closes = [finite_number(b.get("close")) for b in bars]
    if any(v is None or v <= 0 for v in closes):
        return result
    peak_index = max(range(len(bars)-10, len(bars)-1), key=lambda i: closes[i])
    peak = closes[peak_index]
    sma20 = mean(closes[peak_index-19:peak_index+1])
    sma50 = mean(closes[peak_index-49:peak_index+1])
    pct = (1 - closes[-1] / peak) * 100
    lows = [finite_number(b.get("low")) for b in bars[peak_index+1:]]
    support_ok = min(lows) >= sma20 if lows and all(v is not None for v in lows) else None
    volumes = [finite_number(b.get("volume")) for b in bars]
    impulse, retreat = volumes[max(0, peak_index-4):peak_index+1], volumes[peak_index+1:]
    ratio = mean(retreat) / mean(impulse) if retreat and all(v is not None for v in impulse+retreat) and mean(impulse) > 0 else None
    prior_hi = finite_number(bars[-2].get("high"))
    reclaim = closes[-1] > prior_hi if prior_hi else None
    uptrend = peak > sma20 > sma50
    match = uptrend and cfg["pullback_min_pct"] <= pct <= cfg["pullback_max_pct"] and support_ok is True and reclaim is True
    if ratio is not None:
        match = match and ratio < 1
    return {**result, "pullback_pct": pct, "support_distance": (closes[-1]/sma20-1)*100,
            "volume_contraction_ratio": ratio, "prior_uptrend": uptrend, "support_not_broken": support_ok,
            "reclaim_state": "RECLAIM" if reclaim else "NOT_RECLAIMED" if reclaim is False else "NOT_AVAILABLE",
            "pullback_mechanical_match": match, "volume_condition_measurable": ratio is not None}


def freeze_explorer_run(store, *, run_id: str, generated_at: str, market_session: str,
                        all_candidates: list[dict], prescreen_tickers: set[str], final_tickers: set[str],
                        intraday_tickers: set[str], market_breadth: dict | None = None,
                        selection_basis: str = "BROAD_EXPLORER", benchmark: list[dict] | None = None,
                        sample_role: str = "FORWARD_VALIDATION", point_in_time_kind: str = "CONTEMPORANEOUS") -> dict:
    if not market_session or not all_candidates:
        return {"status": "NO_ELIGIBLE_UNIVERSE", "signals_frozen": 0}
    if sample_role not in SAMPLE_ROLES or point_in_time_kind not in POINT_IN_TIME_KINDS:
        raise ValueError("Unknown sample role or point-in-time kind")
    run = start_validation(store, at=generated_at)
    captured = utc_now() if store.environment == "PRODUCTION" else generated_at
    cutoff_dt = parse_dt(captured)
    if cutoff_dt is None:
        raise ValueError("Invalid snapshot clock")
    cfg = run["config"]
    uid = _id(store.environment, run_id, "universe-v070")
    prior = next((r for r in store.validation_records("universe_snapshots") if r["record_id"] == uid), None)
    if prior:
        return {"status": "ALREADY_FROZEN", "universe_snapshot_id": uid, "signals_frozen": 0}
    start_dt = parse_dt(run["FORWARD_VALIDATION_START"])
    cairo = cutoff_dt.astimezone(CAIRO)
    # Exclude any daily session already underway when the evidence was frozen.
    after_day = cairo.date() if (cairo.hour, cairo.minute) >= PRE_OPEN_END else cairo.date()-timedelta(days=1)
    base = {"universe_snapshot_id": uid, "market_session": market_session, "generated_at": generated_at,
            "source_cutoff_timestamp": captured, "signal_timestamp_utc": captured,
            "signal_timestamp_cairo": cairo.isoformat(), "sample_role": sample_role,
            "point_in_time_kind": point_in_time_kind, "enrolled_after_start": cutoff_dt >= start_dt,
            "reconstruction_provenance_verified": False, "synthetic": store.environment != "PRODUCTION",
            "selection_basis": selection_basis, "market_breadth": market_breadth or {},
            "outcome_after_session": max(market_session, after_day.isoformat()),
            "rule_versions": {r["rule_name"]: r["rule_version"] for r in store.validation_records("rule_definitions")}}
    from egxbridge.analysis.schedule.snapshots import build_signal_snapshot, persist_snapshots
    from egxbridge.analysis.schedule.session import session_context
    frozen, members = 0, []
    for rank, c in enumerate(all_candidates, 1):
        ticker = str(c["ticker"]).upper()
        serious = ticker in prescreen_tickers or ticker in final_tickers
        evidence = local_evidence(c, session=market_session, cutoff=captured, cfg=cfg, benchmark=benchmark)
        member = {**base, **evidence, "ticker": ticker, "scanner_rank": c.get("calibrated_rank") or rank,
                  "selection_rank": c.get("calibrated_rank") or rank, "was_scanner_eligible": True,
                  "was_prescreen_selected": ticker in prescreen_tickers,
                  "selected_for_final_handoff": ticker in final_tickers, "selected_for_intraday": ticker in intraday_tickers,
                  "selection_reason": c.get("candidate_reasons") if serious else c.get("exclusion_reason") or "NOT_IN_PRESCREEN_SHORTLIST",
                  "rejection_reason": c.get("exclusion_reason") if not serious else None,
                  "serious_candidate": serious}
        mid = _id(uid, ticker)
        member["member_id"] = mid
        members.append(member)
        if serious:
            snap = build_signal_snapshot(c, run_id=run_id, environment=store.environment, generated_at=captured,
                latest_session=market_session, explorer_run_id=run_id, session_meta=session_context(cutoff_dt))
            stats = persist_snapshots(store, [snap])
            cid = stats["canonical_ids"][0]
            member.update({"canonical_signal_id": cid, "signal_id": cid, "signal_family_id": snap["signal_family_id"],
                           "parent_signal_id": snap.get("parent_signal_id"), "session_phase": snap["session_phase"]})
            frozen += store.append_validation_record("forward_signal_snapshots", cid, member)
            fctx = c.get("funnel_ctx") or c.get("funnel_context") or {}
            fields = fctx.get("structured_fields") or {}
            provenance = fctx.get("structured_provenance") or {}
            # Partial stages have separate evidence clocks. Carry each imported
            # field with its original provenance, never the latest stage's clock.
            sources, source_fields = {}, defaultdict(dict)
            for key, value in fields.items():
                origin = (provenance.get("field_provenance") or {}).get(key) or provenance
                if not origin.get("analysis_imported_at"):
                    continue
                source_id = origin.get("content_hash") or _id(origin)
                sources[source_id] = origin
                source_fields[source_id][key] = value
            for source_id, imported_fields in source_fields.items():
                origin = sources[source_id]
                append_classification(store, cid, ticker=ticker, fields=imported_fields, source="FUNNEL_LLM",
                    source_id=source_id, imported_at=origin["analysis_imported_at"],
                    source_cutoff=origin.get("source_cutoff"),
                    analysis_started_at=origin.get("analysis_started_at"),
                    market_data_cutoff=origin.get("market_data_cutoff"),
                    funnel_version=origin.get("funnel_version") or fctx.get("funnel_version"), carried_forward=True)
        store.append_validation_record("universe_snapshot_members", mid, member)
    store.append_validation_record("universe_snapshots", uid, {**base, "eligible_n": len(members), "run_id": run_id})
    return {"status": "FROZEN", "universe_snapshot_id": uid, "signals_frozen": frozen, "eligible_n": len(members)}


def append_classification(store, canonical_signal_id: str, *, ticker: str, fields: dict, source: str,
                          source_id: str, imported_at: str | None = None, source_cutoff: str | None = None,
                          funnel_version: str | None = None, schedule_version: str | None = None,
                          analysis_started_at: str | None = None, market_data_cutoff: str | None = None, observation_id: str | None = None,
                          carried_forward: bool = False, schedule_status: str | None = None) -> dict:
    if source not in {"FUNNEL_LLM", "SCHEDULE_LLM"}:
        raise ValueError("Economic/expectations judgments require an imported LLM source")
    signal = store.get_canonical_signal(canonical_signal_id)
    if not signal or signal["environment"] != store.environment or signal["ticker"] != ticker.upper():
        raise ValueError("Classification canonical identity/ticker/environment mismatch")
    normalized, issues = normalize_fields(fields)
    stamp = imported_at or utc_now()
    if parse_dt(stamp) is None:
        raise ValueError("Invalid import timestamp")
    if store.environment == "PRODUCTION" and not carried_forward:
        stamp = utc_now()
    cutoff = parse_dt(source_cutoff)
    market_cutoff = parse_dt(market_data_cutoff)
    market_clock_valid = market_data_cutoff is None or (market_cutoff is not None and market_cutoff <= parse_dt(stamp))
    timing = "DECLARED_CUTOFF_AVAILABLE" if cutoff and cutoff <= parse_dt(stamp) and market_clock_valid else "CUTOFF_NOT_RELIABLE"
    rec = {"canonical_signal_id": canonical_signal_id, "ticker": ticker.upper(), "fields": normalized,
           "classification_source": source, "classification_timestamp": stamp,
           "analysis_imported_at": stamp, "analysis_started_at": analysis_started_at, "market_data_cutoff": market_data_cutoff,
           "source_cutoff": source_cutoff, "declared_research_cutoff": source_cutoff,
           "funnel_version": funnel_version, "schedule_version": schedule_version,
           "source_id": source_id, "analysis_observation_id": observation_id,
           "schema_issues": issues, "timing_integrity": timing, "carried_forward": carried_forward,
           "schedule_status": schedule_status, "decision_kind": "IMPORTED_LLM_DECISION"}
    key = _id(canonical_signal_id, source, source_id, observation_id)
    store.append_validation_record("forward_signal_classifications", key, rec)
    return rec


def append_later_review(store, cid: str, *, ticker: str, fields: dict, source_id: str, cutoff: str | None) -> bool:
    signal = store.get_canonical_signal(cid)
    if not signal or signal["environment"] != store.environment or signal["ticker"] != ticker.upper():
        raise ValueError("Later review identity mismatch")
    normalized, issues = normalize_fields(fields, later=True)
    return store.append_validation_record("later_event_reviews", _id(cid, source_id, "later"), {
        "canonical_signal_id": cid, "ticker": ticker.upper(), "fields": normalized,
        "event_source_cutoff": cutoff, "reviewed_at": utc_now(), "classification_source": "WEEKLY_LLM",
        "source_id": source_id, "schema_issues": issues})


def store_change_proposal(store, proposal: dict, *, source: str, source_id: str) -> dict:
    if source != "WEEKLY_LLM":
        raise ValueError("Only imported Weekly X-Ray may propose rule changes")
    if not isinstance(proposal, dict):
        raise ValueError("Weekly proposal must be an object")
    required = {"rule_name", "old_definition", "proposed_definition", "reason", "sample_window", "independent_N",
                "group_statistics", "friction_included", "regime_splits", "known_limitations", "expected_effect"}
    action = proposal.get("action")
    if action not in {"KEEP_RULE", "INVESTIGATE_RULE", "PROPOSE_CHANGE"} or required - proposal.keys():
        raise ValueError("Incomplete Weekly rule proposal")
    rec = {**proposal, "requires_forward_confirmation": "YES", "status": "PENDING_EXTERNAL_REVIEW",
           "origin": source, "source_id": source_id, "stored_at": utc_now(), "auto_applied": False,
           "discovery_for_new_rule": proposal["sample_window"], "new_rule_validation": "LATER_CHRONOLOGICAL_SAMPLE_REQUIRED"}
    store.append_validation_record("rule_change_proposals", _id(source_id, proposal), rec)
    return rec


def _class_known_before_outcome(classification: dict, outcome: dict, snapshot: dict) -> bool:
    if classification.get("timing_integrity") != "DECLARED_CUTOFF_AVAILABLE":
        return False
    imported = parse_dt(classification.get("analysis_imported_at"))
    after = snapshot.get("outcome_after_session") or snapshot.get("market_session")
    if not after:
        return False
    # Missing provider bars must never extend classification availability. Without
    # a verified holiday calendar, close the window at the next possible session.
    day = datetime.fromisoformat(after).date() + timedelta(days=1)
    while day.weekday() in (4, 5):
        day += timedelta(days=1)
    boundary = datetime.combine(day, datetime.min.time(), tzinfo=CAIRO).replace(
        hour=PRE_OPEN_END[0], minute=PRE_OPEN_END[1])
    dates = outcome.get("session_dates") or []
    if dates:
        boundary = min(boundary, datetime.fromisoformat(dates[0]).replace(
            hour=PRE_OPEN_END[0], minute=PRE_OPEN_END[1], tzinfo=CAIRO))
    return bool(imported and boundary and imported <= boundary)


def joined_signals(store, *, include_reconstructed: bool = False) -> tuple[list[dict], list[dict]]:
    snapshots = [s for s in store.validation_records("forward_signal_snapshots") if eligible_sample(s, include_reconstructed=include_reconstructed)]
    outcomes = {o["canonical_signal_id"]: json.loads(o["payload_json"]) for o in store.list_canonical_outcomes(limit=-1)}
    classifications = defaultdict(list)
    for c in store.validation_records("forward_signal_classifications"):
        classifications[c["canonical_signal_id"]].append(c)
    rows, observations = [], []
    observed_units = set()
    for s in snapshots:
        cid = s["canonical_signal_id"]
        o = outcomes.get(cid) or {}
        if o.get("source_cutoff_timestamp") != s.get("source_cutoff_timestamp"):
            o = {}
        row = {**s, **o, "canonical_signal_id": cid, "llm_fields": {}, "llm_provenance": {},
               "funnel_analyzed": False, "excluded_late_classifications": 0}
        classes = sorted(classifications[cid], key=lambda c: parse_dt(c["analysis_imported_at"]))
        for c in classes:
            if not _class_known_before_outcome(c, o, s):
                row["excluded_late_classifications"] += 1
                continue
            if (c.get("classification_source") == "FUNNEL_LLM" and str(c.get("funnel_version")).endswith("2.8")
                    and any(c["fields"].get(k) is not None and c["fields"][k] not in MISSING_VALUES for k in
                            ("price_implied_expectations", "expectations_gap", "expectations_revision_outlook"))):
                row["funnel_analyzed"] = True
            for key, value in c["fields"].items():
                if isinstance(value, str) and value in MISSING_VALUES:
                    continue
                # Earliest available classification wins; later opinions cannot rewrite T0.
                row["llm_fields"].setdefault(key, value)
                row["llm_provenance"].setdefault(key, {k: c.get(k) for k in ("classification_source", "funnel_version", "analysis_imported_at", "source_cutoff")})
            if c["classification_source"] == "SCHEDULE_LLM" and c.get("schedule_status") in {"PROMOTE", "DOWNGRADE", "REMOVE", "KEEP", "WATCH_ONLY"}:
                unit_key = (cid, c.get("analysis_observation_id") or c["record_id"])
                if unit_key in observed_units:
                    continue
                observed_units.add(unit_key)
                observations.append({**row, "classification_record_id": c["record_id"],
                    "analysis_observation_id": c.get("analysis_observation_id"), "schedule_status": c["schedule_status"],
                    "unit": "canonical_signal_id + imported analysis observation"})
        row.update(row["llm_fields"])
        rows.append(row)
    return rows, observations


def sample_statistics(rows: list[dict], *, cfg: dict | None = None, unit: str = "canonical_signal_id") -> dict:
    cfg = cfg or DEFAULT_CONFIG
    ids = {r.get("canonical_signal_id") or r.get("member_id") for r in rows}
    independent = {r.get("signal_family_id") or r.get("canonical_signal_id") or r.get("member_id") for r in rows}
    tickers = Counter(r["ticker"] for r in rows)
    sectors = {r.get("sector") for r in rows} - {None, "UNKNOWN"}
    regimes = {r.get("market_tape_regime_local_input") for r in rows} - {None, "NOT_RELIABLE"}
    dates = sorted({r.get("market_session") for r in rows if r.get("market_session")})
    concentration = max(tickers.values()) / len(rows) if rows else None
    diversity = "NOT_RELIABLE" if not rows else "HIGHLY_CONCENTRATED" if concentration > .5 or len(tickers) < 3 else "CONCENTRATED" if concentration > .2 or len(tickers) < 10 else "GOOD"
    result = {"N": len(rows) if unit != "canonical_signal_id" else len(ids), "unit": unit,
              "independent_signal_n": len(independent), "unique_ticker_n": len(tickers),
              "unique_sector_n": len(sectors), "market_regime_n": len(regimes),
              "date_span": [dates[0], dates[-1]] if dates else [], "sample_diversity_status": diversity,
              "largest_ticker_share": concentration, "interpretation": "DESCRIPTIVE_ONLY",
              "rate_label": "EMPIRICAL POSITIVE-RETURN RATE", "horizons": {}}
    for h in HORIZONS + (60,):
        mature = [r for r in rows if r.get(f"maturity_{h}") == "MATURE" and finite_number(r.get(f"return_{h}")) is not None
                  and r.get(f"integrity_{h}") != "NOT_RELIABLE"]
        values = [r[f"return_{h}"] for r in mature]
        ni = len({r.get("signal_family_id") or r.get("canonical_signal_id") or r.get("member_id") for r in mature})
        band = "DESCRIPTIVE_ONLY" if ni < cfg["descriptive_below"] else "PROVISIONAL" if ni < cfg["review_eligible_at"] else "CALIBRATION_REVIEW_ELIGIBLE"
        stats = {"N": len(mature), "independent_signal_n": ni, "pending_n": len(rows)-len(mature),
                 "median_return": median(values) if values else None, "mean_return": mean(values) if values else None,
                 "empirical_positive_return_rate": sum(v > 0 for v in values) / len(values) if values else None,
                 "interpretation": band, "group_evidence": "INSUFFICIENT_SAMPLE" if ni < cfg["minimum_group_n"] else band}
        for key in ("mfe", "mae", "net_return_after_friction"):
            vals = [r[f"{key}_{h}"] for r in mature if finite_number(r.get(f"{key}_{h}")) is not None]
            stats[f"median_{key}"] = median(vals) if vals else None
            stats[f"{key}_n"] = len(vals)
        if any(r.get("round_level") is not None for r in rows):
            encounters = [event for r in mature for event in r.get(f"round_number_outcomes_{h}") or []
                          if event.get("round_level") == r.get("round_level") and event.get("status") != "NOT_RELIABLE"]
            stats["round_encounter_n"] = len(encounters)
            for event in ("touch", "rejection", "breakout", "close_above", "close_below"):
                stats[f"empirical_{event}_rate"] = sum(e.get(event) is True for e in encounters) / len(encounters) if encounters else None
        result["horizons"][str(h)] = stats
    result["interpretation"] = result["horizons"]["20"]["interpretation"]
    result["signal_calibration_status"] = "INSUFFICIENT_SAMPLE" if not rows else "DESCRIPTIVE" if result["interpretation"] == "DESCRIPTIVE_ONLY" else result["interpretation"]
    return result


def group_report(rows: list[dict], fields: tuple[str, ...], *, cfg: dict | None = None, unit: str = "canonical_signal_id") -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        key = tuple(str(row.get(f)) if row.get(f) is not None else "NOT_ANALYZED" for f in fields)
        groups[key].append(row)
    return [{**dict(zip(fields, key)), **sample_statistics(group, cfg=cfg, unit=unit)} for key, group in sorted(groups.items())]


def _volume_bin(v):
    v = finite_number(v)
    return "NOT_AVAILABLE" if v is None else "<1.0" if v < 1 else "1.0–1.5" if v <= 1.5 else "1.5–2.0" if v <= 2 else ">2.0"


def _missed_reason(row: dict) -> str:
    reason = str(row.get("rejection_reason") or "").upper()
    if row.get("technical_history_integrity") in {"POSSIBLE_DISCONTINUITY", "NOT_RELIABLE"}:
        return "HISTORY_INTEGRITY_BLOCK"
    mapping = {"LIQUIDITY": "LIQUIDITY_FILTER", "DATA_UNAVAILABLE": "DATA_UNAVAILABLE", "SCORE_THRESHOLD": "BELOW_SCORE_THRESHOLD",
               "LANE_PRIORITY": "WRONG_LANE_PRIORITY", "NOT_EXECUTABLE": "NOT_EXECUTABLE", "VOLUME": "NO_VOLUME_CONFIRMATION", "WEAK_RS": "WEAK_RS"}
    return next((label for token, label in mapping.items() if token in reason), "UNEXPLAINED")


def false_negative_report(store, *, horizon: int = 10, cfg: dict | None = None, members: list | None = None, outcomes: dict | None = None) -> dict:
    cfg = cfg or (validation_run(store) or {}).get("config") or DEFAULT_CONFIG
    members = [r for r in (members if members is not None else store.validation_records("universe_snapshot_members")) if eligible_sample(r)]
    outcomes = outcomes if outcomes is not None else {o["record_id"]: o for o in store.validation_records("universe_member_outcomes")}
    by_universe = defaultdict(list)
    for m in members:
        by_universe[m["universe_snapshot_id"]].append({**m, **(outcomes.get(m["record_id"]) or {})})
    missed, coverage = [], []
    for uid, group in by_universe.items():
        mature = [r for r in group if r.get(f"maturity_{horizon}") == "MATURE" and r.get(f"integrity_{horizon}") != "NOT_RELIABLE"]
        mature.sort(key=lambda r: (-r[f"return_{horizon}"], r["ticker"]))
        n = math.ceil(len(mature)*cfg["false_negative_top_fraction"]) if cfg.get("false_negative_top_fraction") else cfg["false_negative_top_n"]
        coverage.append({"universe_snapshot_id": uid, "eligible_n": len(group), "mature_n": len(mature),
                         "missing_or_pending_n": len(group)-len(mature), "ranking_scope": "MATURE_AVAILABLE_UNIVERSE"})
        for rank, row in enumerate(mature[:n], 1):
            if not row.get("selected_for_final_handoff"):
                missed.append({**row, "forward_rank": rank, "horizon": horizon, "MISSED_REASON": _missed_reason(row),
                               "audit_interpretation": "REVIEW_CANDIDATE", "universe_mature_n": len(mature), "universe_eligible_n": len(group)})
    return {"horizon": horizon, "selection_rule": {"top_n": cfg["false_negative_top_n"], "top_fraction": cfg.get("false_negative_top_fraction")},
            "coverage": coverage, "cases": missed, "note": "Unselected T0 members retained. Missing future data is disclosed; it is never a zero return."}


def validation_report(store) -> dict:
    run = validation_run(store)
    cfg = (run or {}).get("config") or DEFAULT_CONFIG
    rows, observations = joined_signals(store)
    for r in rows:
        r["volume_ratio_bin"] = _volume_bin(r.get("volume_ratio_20d"))
        clv = finite_number(r.get("CLV"))
        r["CLV_bin"] = "NOT_AVAILABLE" if clv is None else "LOW" if clv < -.33 else "MID" if clv < .33 else "HIGH"
        rs = finite_number(r.get("RS20"))
        r["RS_state"] = "NOT_AVAILABLE" if rs is None else "POSITIVE" if rs > 0 else "NON_POSITIVE"
        rs5 = finite_number(r.get("RS5"))
        r["RS_direction_5"] = "NOT_AVAILABLE" if rs5 is None else "RISING_LAST_5" if rs5 > 0 else "FALLING_OR_FLAT_LAST_5"
        r["day_of_week"] = datetime.fromisoformat(r["market_session"]).strftime("%A")
        fv = finite_number(r.get("central_fv"))
        price = finite_number(r.get("price_t0"))
        rev, expectation = r.get("expectations_revision_outlook"), r.get("price_implied_expectations")
        up = rev in {"UPWARD", "STRONG_UPWARD"}
        down = rev in {"DOWNWARD", "STRONG_DOWNWARD"}
        r["premium_fv_group"] = None
        r["discount_fv_group"] = None
        if r["funnel_analyzed"] and fv and price:
            if price > fv:
                r["premium_fv_group"] = "A_REASONABLE_UPWARD" if expectation in {"REASONABLE", "UNDEMANDING"} and up else "B_DEMANDING_DOWNWARD" if expectation in {"DEMANDING", "VERY_DEMANDING"} and down else "C_OTHER"
            elif price < fv:
                r["discount_fv_group"] = "DISCOUNT_UPWARD" if up else "DISCOUNT_DOWNWARD" if down else "DISCOUNT_OTHER"
    cohorts = {
        "ALL_SERIOUS_CANDIDATES": rows,
        "FINAL_HANDOFF": [r for r in rows if r.get("selected_for_final_handoff")],
        "LLM_PROMOTED": [r for r in observations if r.get("schedule_status") == "PROMOTE"],
        "LLM_DOWNGRADED": [r for r in observations if r.get("schedule_status") in {"DOWNGRADE", "REMOVE"}],
        "FUNNEL_ANALYZED": [r for r in rows if r["funnel_analyzed"]],
    }
    all_members = store.validation_records("universe_snapshot_members")
    latent = [r for r in all_members if eligible_sample(r) and not r.get("selected_for_final_handoff")]
    member_outcomes = {o["record_id"]: o for o in store.validation_records("universe_member_outcomes")}
    latent = [{**r, **(member_outcomes.get(r["record_id"]) or {})} for r in latent]
    summary = sample_statistics(rows, cfg=cfg)
    expectations = {
        "burden_revision": group_report(rows, ("price_implied_expectations", "expectations_revision_outlook"), cfg=cfg),
        "expectations_burden": group_report(rows, ("expectations_burden", "expectations_revision_outlook"), cfg=cfg),
        "gap_revision": group_report(rows, ("expectations_gap", "expectations_revision_outlook"), cfg=cfg),
        "premium_to_fv": group_report([r for r in rows if r["premium_fv_group"]], ("premium_fv_group",), cfg=cfg),
        "discount_to_fv": group_report([r for r in rows if r["discount_fv_group"]], ("discount_fv_group",), cfg=cfg),
        "catalyst_revision": group_report(rows, ("catalyst_revision_potential",), cfg=cfg),
        "information_reaction": group_report(rows, ("information_reaction_regime",), cfg=cfg),
        "intrinsic_value_position": group_report(rows, ("intrinsic_value_position",), cfg=cfg),
        "rerating_attribution": group_report(rows, ("rerating_attribution",), cfg=cfg),
    }
    breakouts = [r for r in rows if r.get("breakout_close_acceptance") is True]
    pullbacks = [r for r in rows if r.get("pullback_mechanical_match") is True]
    psychology = []
    for r in rows:
        for level in r.get("psychological_levels") or []:
            if isinstance(level, dict):
                psychology.append({**r, **level, "PLSS_status": "HEURISTIC"})
    rounds = [{**r, **level} for r in rows for level in r.get("round_number_encounters") or []]
    regime_fields = ("market_tape_regime_local_input", "day_of_week", "market_liquidity_regime", "market_cap_bucket", "catalyst_type", "sector", "candidate_lane", "forward_setup_quality", "move_already_realized")
    return {
        "FORWARD_VALIDATION_START": (run or {}).get("FORWARD_VALIDATION_START"),
        "status": (run or {}).get("status") or "NOT_STARTED", "synthetic": store.environment != "PRODUCTION",
        "environment": store.environment, "summary": summary,
        "sample_integrity": {"enrolled_signals_n": len(store.validation_records("forward_signal_snapshots")),
            "forward_validation_n": len(rows), "excluded_late_classifications": sum(r["excluded_late_classifications"] for r in rows),
            "missing_price_n": sum(r.get("price_t0") is None for r in rows), "default_sample_kind": "CONTEMPORANEOUS"},
        "cohorts": {**{name: sample_statistics(group, cfg=cfg, unit="canonical_signal_id + imported analysis observation" if name.startswith("LLM_") else "canonical_signal_id") for name, group in cohorts.items()},
                    "NOT_SELECTED_LATENT_UNIVERSE": sample_statistics(latent, cfg=cfg, unit="universe_snapshot_id + ticker")},
        "expectations": expectations,
        "breakouts": {"bin_status": "INITIAL_ANALYSIS_BINS", **{f: group_report(breakouts, (f,), cfg=cfg) for f in ("volume_ratio_bin", "CLV_bin", "RS_state", "catalyst_status", "price_implied_expectations", "market_tape_regime_local_input")}},
        "pullbacks": {f: group_report(pullbacks, (f,), cfg=cfg) for f in ("RS_direction_5", "RS_state", "catalyst_status", "reclaim_state")},
        "psychology": {"PLSS_status": "HEURISTIC", "levels": psychology,
            "coverage_groups": group_report(psychology, ("PLSS_evidence_coverage",), cfg=cfg, unit="canonical_signal_id + level"),
            "round_number_encounters": rounds,
            "round_groups": group_report(rounds, ("round_level",), cfg=cfg, unit="canonical_signal_id + round level")},
        "regimes": {f: group_report(rows, (f,), cfg=cfg) for f in regime_fields},
        "false_positives": [r for r in rows if r.get("forward_setup_quality") == "STRONG" and
            ((r.get("return_10") is not None and r["return_10"] < cfg["poor_return_10_pct"]) or
             (r.get("mae_10") is not None and r["mae_10"] < cfg["adverse_mae_pct"]))],
        "false_negatives": {str(h): false_negative_report(store, horizon=h, cfg=cfg, members=all_members, outcomes=member_outcomes) for h in (5, 10, 20)},
        "rule_versions": store.validation_records("rule_definitions"),
        "change_proposals": store.validation_records("rule_change_proposals"),
        "later_event_reviews": store.validation_records("later_event_reviews"),
        "signals": rows, "llm_value_add_observations": observations,
        "limitations": ["Scanner selection is heuristic and under forward validation.",
            "Expectations classifications shown here come from Funnel/ChatGPT analysis.",
            "Outcome statistics are descriptive until sufficient independent sample accumulates.",
            "The app prepares evidence and tracks results. It does not make the final investment decision.",
            "Independent N counts signal families; repeated ticker and regime concentration remain disclosed.",
            "Daily OHLC cannot resolve same-session target/stop order; reference-price returns do not establish fillability.",
            "No official exchange holiday calendar locally. Horizons count observed completed trading bars; missing bars remain a data limitation.",
            "Late or unverifiable-cutoff classifications are excluded from T0 predictive groups."]}


def weekly_package(store, output_dir: Path) -> dict:
    from egxbridge.analysis.common.packaging import write_json, write_text
    report = validation_report(store)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "forward_validation_audit.json", report)
    write_text(output_dir / "forward_validation_audit.md", "# FORWARD VALIDATION AUDIT\n\n" +
        "WEEKLY X-RAY is the validation interpretation owner. All supplied statistics are APP_GENERATED.\n\n" +
        "Review sample integrity; scanner outcomes; expectations; setups; false positives; false negatives; regimes; friction; rule versions. " +
        "Return KEEP_RULE / INVESTIGATE_RULE / PROPOSE_CHANGE. Never activate or retune rules. " +
        "A changed rule needs later chronological data; the motivating sample is DISCOVERY_FOR_NEW_RULE.\n\n" +
        "\n".join(report["limitations"]) + "\n\n```json\n" + json.dumps(report["summary"], indent=2) + "\n```\n")
    return report


def main(argv=None) -> int:
    import argparse
    from egxbridge.analysis.common.environment import analysis_db_path_for
    from egxbridge.analysis.common.persistence import AnalysisStore
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("summary", "expectations", "breakouts", "pullbacks", "psychology", "false-negatives", "weekly-package"):
        parser.add_argument(f"--{flag}", action="store_true")
    parser.add_argument("--environment", default="PRODUCTION")
    parser.add_argument("--output-dir", type=Path, default=Path("output/forward_validation"))
    args = parser.parse_args(argv)
    store = AnalysisStore(analysis_db_path_for(args.environment), environment=args.environment)
    try:
        report = weekly_package(store, args.output_dir) if args.weekly_package else validation_report(store)
        sections = [key for key in ("summary", "expectations", "breakouts", "pullbacks", "psychology", "false_negatives") if getattr(args, key)]
        print(json.dumps({k: report[k] for k in sections} if sections else report, indent=2, default=str))
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
