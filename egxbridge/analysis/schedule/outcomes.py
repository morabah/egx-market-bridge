"""Deterministic outcome math on trading sessions. Does not retune scores."""
from __future__ import annotations

from typing import Any
from datetime import datetime, timedelta, timezone
import math

from egxbridge.analysis.schedule.session import CAIRO, TRADING_AT_LAST_END, parse_dt

from egxbridge.analysis.schedule.types import SCORING_VERSION


POSITIVE_CLOSE_THRESHOLD = 0.0
TACTICAL_SUCCESS_THRESHOLD_PCT = 1.0
DISCONTINUITY_RATIO = 0.45


def _session_key(bar: dict[str, Any]) -> str | None:
    return bar.get("session_date") or (str(bar.get("normalized_utc_timestamp") or bar.get("timestamp") or "")[:10] or None)


def _px(bar: dict[str, Any], field: str) -> float | None:
    v = bar.get(field)
    try:
        if v is None or isinstance(v, bool):
            return None
        n = float(v)
        return n if math.isfinite(n) and n > 0 else None
    except Exception:
        return None


def unique_trading_sessions(bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One bar per trading session, chronological. Calendar weekends are not invented."""
    by: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for b in bars:
        k = _session_key(b)
        if not k:
            continue
        if k not in by:
            by[k] = b
            order.append(k)
        else:
            # prefer bar with high/low if later duplicate
            if _px(b, "high") is not None:
                by[k] = b
    order.sort()
    return [by[k] for k in order]


def sessions_after(bars: list[dict[str, Any]], after_session: str | None) -> list[dict[str, Any]]:
    sessions = unique_trading_sessions(bars)
    if not after_session:
        return sessions
    return [b for b in sessions if (_session_key(b) or "") > after_session]


def _mfe_mae(baseline: float, future: list[dict[str, Any]], n: int) -> tuple[float | None, float | None]:
    """Long-tactical: MFE from highs, MAE from lows. Documented direction assumption."""
    window = future[:n]
    if len(window) < n or not baseline:
        return None, None
    mfe = None
    mae = None
    for b in window:
        hi = _px(b, "high")
        lo = _px(b, "low")
        close = _px(b, "close")
        if hi is None or lo is None or close is None or not lo <= close <= hi:
            return None, None
        if hi is not None:
            fav = (hi / baseline - 1.0) * 100.0
            mfe = fav if mfe is None else max(mfe, fav)
        if lo is not None:
            adv = (lo / baseline - 1.0) * 100.0
            mae = adv if mae is None else min(mae, adv)
    return (
        None if mfe is None else round(mfe, 4),
        None if mae is None else round(mae, 4),
    )


def _ret(baseline: float, bar: dict[str, Any] | None) -> float | None:
    if bar is None or not baseline:
        return None
    c = _px(bar, "close")
    if c is None:
        return None
    return round((c / baseline - 1.0) * 100.0, 4)


def path_has_discontinuity(future: list[dict[str, Any]], baseline: float) -> bool:
    prev = baseline
    for b in future:
        c = _px(b, "close")
        if c is None or not prev:
            continue
        if abs(c / prev - 1.0) > DISCONTINUITY_RATIO:
            return True
        prev = c
    return False


def compute_outcomes(
    *,
    baseline_price: float | None,
    baseline_timestamp: str | None,
    baseline_type: str,
    signal_session: str | None,
    future_bars: list[dict[str, Any]],
    history_integrity: str | None = None,
    horizons: tuple[int, ...] = (1, 2, 3, 5, 10, 20),
) -> dict[str, Any]:
    """
    Trading-session returns only. Holiday/weekend gaps do not count as sessions.

    Definitions (explicit):
      POSITIVE_CLOSE = next-horizon close return > 0
      TACTICAL_SUCCESS = next-horizon close return >= 1.0%  (configurable)
      MFE_n / MAE_n use high/low over the next n trading sessions.
      Direction assumption: LONG_TACTICAL (high=favorable, low=adverse).
    """
    baseline = _px({"baseline": baseline_price}, "baseline")
    if baseline is None:
        return {
            "outcome_status": "NOT_EVALUABLE",
            "outcome_baseline_price": baseline_price,
            "outcome_baseline_timestamp": baseline_timestamp,
            "outcome_baseline_type": baseline_type,
            "reason": "missing_baseline_price",
            "scoring_version": SCORING_VERSION,
        }
    future = sessions_after(future_bars, signal_session)
    n = len(future)
    integrity_warning = history_integrity in {"POSSIBLE_DISCONTINUITY", "NOT_RELIABLE"} or path_has_discontinuity(future, baseline)
    if n == 0:
        status = "PENDING"
    elif n >= 5:
        status = "COMPLETE_FOR_5D"
    elif n >= 1:
        status = "PARTIAL"
    else:
        status = "PENDING"

    out: dict[str, Any] = {
        "outcome_status": status,
        "outcome_baseline_price": baseline,
        "outcome_baseline_timestamp": baseline_timestamp,
        "outcome_baseline_type": baseline_type,
        "sessions_available": n,
        "session_dates": [_session_key(b) for b in future[:max(set(horizons) | {20})]],
        "next_session_return": _ret(baseline, future[0] if n >= 1 else None),
        "return_3_sessions": _ret(baseline, future[2] if n >= 3 else None),
        "return_5_sessions": _ret(baseline, future[4] if n >= 5 else None),
        "return_10_sessions": _ret(baseline, future[9] if n >= 10 else None),
        "direction_assumption": "LONG_TACTICAL",
        "positive_close_definition": "future return > 0",
        "tactical_success_definition": f"future return >= {TACTICAL_SUCCESS_THRESHOLD_PCT}%",
        "outcome_integrity_warning": integrity_warning,
        "history_integrity": history_integrity,
        "scoring_version_untouched": SCORING_VERSION,
        "calendar_days_not_used": True,
    }
    for h in sorted(set(horizons) | {1, 2, 3, 5, 10, 20}):
        mature = n >= h
        warning = history_integrity in {"POSSIBLE_DISCONTINUITY", "NOT_RELIABLE"} or path_has_discontinuity(future[:h], baseline)
        out[f"return_{h}"] = _ret(baseline, future[h - 1]) if mature else None
        out[f"return_{h}_sessions"] = out[f"return_{h}"]
        mfe, mae = _mfe_mae(baseline, future, h) if mature and not warning else (None, None)
        out[f"mfe_{h}"] = mfe
        out[f"mae_{h}"] = mae
        out[f"MFE_{h}"] = mfe
        out[f"MAE_{h}"] = mae
        out[f"integrity_{h}"] = "NOT_RELIABLE" if warning else "NO_DISCONTINUITY_DETECTED"
        out[f"maturity_{h}"] = "MATURE" if mature and out[f"return_{h}"] is not None else "PENDING"
    out["horizons_complete"] = all(out.get(f"maturity_{h}") == "MATURE" for h in horizons)
    if 1 in horizons and out["next_session_return"] is not None:
        out["positive_close_1"] = out["next_session_return"] > POSITIVE_CLOSE_THRESHOLD
        out["tactical_success_1"] = out["next_session_return"] >= TACTICAL_SUCCESS_THRESHOLD_PCT
    return out


def completed_through(at: datetime | None = None) -> str:
    """Calendar cutoff for observed bars; today's bar is eligible from cash close.

    This does not assert that a session exists on a weekend or unknown holiday.
    """
    cairo = (parse_dt(at) or datetime.now(timezone.utc)).astimezone(CAIRO)
    day = cairo.date()
    if (cairo.hour, cairo.minute) < TRADING_AT_LAST_END:
        day -= timedelta(days=1)
    return day.isoformat()


def friction_outcome(gross: float | None, model: dict | None) -> dict:
    """Costs are percentage points. No zero-cost assumption for missing inputs."""
    model = model or {}
    components = model.get("components_pct") or {}
    required = ("brokerage", "exchange_regulatory", "taxes", "spread", "slippage")
    valid = {k: float(v) for k, v in components.items()
             if k in required + ("entry", "exit") and isinstance(v, (int, float))
             and not isinstance(v, bool) and math.isfinite(v) and v >= 0}
    complete = all(k in valid for k in required) and bool(model.get("friction_inputs_source"))
    status = ("OBSERVED" if model.get("observed") else "ESTIMATED") if complete else ("PARTIAL" if valid else "NOT_AVAILABLE")
    total = sum(valid.values()) if complete else None
    return {"friction_status": status, "friction_model_version": model.get("friction_model_version"),
            "friction_inputs_source": model.get("friction_inputs_source"),
            "estimated_total_friction": total, "known_partial_friction": sum(valid.values()) if valid else None,
            "net_return_after_friction": round(gross - total, 4) if gross is not None and total is not None else None}


def target_stop_outcome(snapshot: dict, future: list[dict]) -> dict:
    target = _px(snapshot, "target_price_t0")
    stop = _px(snapshot, "stop_or_invalidation_t0")
    out = {"target_hit": None, "stop_hit": None, "target_hit_session": None,
           "stop_hit_session": None, "target_before_stop": "NOT_APPLICABLE"}
    if target is None and stop is None:
        return out
    if not future:
        return {**out, "target_before_stop": "NOT_RELIABLE"}
    if any(_px(b, "high") is None or _px(b, "low") is None or _px(b, "high") < _px(b, "low") for b in future):
        return {**out, "target_before_stop": "NOT_RELIABLE"}
    th = next((_session_key(b) for b in future if target and _px(b, "high") >= target), None)
    sh = next((_session_key(b) for b in future if stop and _px(b, "low") <= stop), None)
    ordering = "NOT_APPLICABLE"
    if target is not None and stop is not None:
        ordering = ("SAME_SESSION_AMBIGUOUS" if th and th == sh else
                    "YES" if th and (not sh or th < sh) else "NO" if sh else "NOT_APPLICABLE")
    return {"target_hit": bool(th) if target else None, "stop_hit": bool(sh) if stop else None,
            "target_hit_session": th, "stop_hit_session": sh, "target_before_stop": ordering}


def outcome_for_snapshot(snapshot: dict, bars: list[dict], *, horizons: tuple[int, ...], through_session: str) -> dict:
    cutoff = snapshot.get("outcome_after_session") or snapshot.get("market_session")
    future = sessions_after([b for b in bars if (_session_key(b) or "") <= through_session
                             and b.get("is_complete") is not False], cutoff)
    out = compute_outcomes(baseline_price=snapshot.get("price_t0"), baseline_timestamp=snapshot.get("price_timestamp"),
                           baseline_type=snapshot.get("price_basis") or "OFFICIAL_CLOSE", signal_session=cutoff,
                           future_bars=future, history_integrity=snapshot.get("technical_history_integrity"), horizons=horizons)
    out.update({"ticker": snapshot["ticker"], "through_session": through_session,
                "canonical_signal_id": snapshot.get("canonical_signal_id"), "source_cutoff_timestamp": snapshot.get("source_cutoff_timestamp")})
    # compute_outcomes retains all core horizons for existing consumers. Every
    # mature horizon needs the matching friction and event evidence as well.
    for h in sorted(set(horizons) | {1, 2, 3, 5, 10, 20}):
        costs = friction_outcome(out.get(f"return_{h}"), snapshot.get("friction_model"))
        out.update({k: v for k, v in costs.items() if k != "net_return_after_friction"})
        out[f"net_return_after_friction_{h}"] = costs["net_return_after_friction"]
        if out.get(f"maturity_{h}") == "MATURE":
            events = target_stop_outcome(snapshot, future[:h])
            if out.get(f"integrity_{h}") == "NOT_RELIABLE":
                events = {**events, "target_hit": None, "stop_hit": None, "target_before_stop": "NOT_RELIABLE"}
            out[f"target_stop_{h}"] = events
            encounters = []
            for level in snapshot.get("round_number_encounters") or []:
                px = level["round_level"]
                path = future[:h]
                valid = all(_px(b, "high") and _px(b, "low") and _px(b, "close")
                            and _px(b, "low") <= _px(b, "close") <= _px(b, "high") for b in path)
                if not valid:
                    encounters.append({"round_level": px, "status": "NOT_RELIABLE"})
                    continue
                touch = any(_px(b, "low") <= px <= _px(b, "high") for b in path)
                prior_closes = [snapshot.get("price_t0")] + [_px(b, "close") for b in path[:-1]]
                encounters.append({"round_level": px, "touch": touch,
                    "rejection": any(_px(b, "high") >= px and _px(b, "close") < px for b in path),
                    "breakout": any(prior is not None and prior <= px < _px(b, "close")
                                    for prior, b in zip(prior_closes, path)),
                    "close_above": _px(path[-1], "close") > px, "close_below": _px(path[-1], "close") < px})
            out[f"round_number_outcomes_{h}"] = encounters
    return out


def update_outcomes_for_store(store, db, *, pending_only: bool = True, through_session: str | None = None,
                              dry_run: bool = False, horizons: tuple[int, ...] = (1, 2, 5, 10, 20),
                              forward_validation_only: bool = False) -> dict[str, Any]:
    """One math owner for canonical and full-universe outcomes; dry-run never backfills."""
    if not horizons or any(h not in {1, 2, 3, 5, 10, 20, 60} for h in horizons):
        raise ValueError("Unsupported trading-session horizon")
    from egxbridge.analysis.schedule.identity import backfill_canonical_from_legacy_snapshots
    from egxbridge.analysis.forward_validation import eligible_sample, _class_known_before_outcome
    import json
    if not dry_run and not forward_validation_only:
        backfill_canonical_from_legacy_snapshots(store)
    through = min(through_session or completed_through(), completed_through())
    forwards = {s["canonical_signal_id"]: s for s in store.validation_records("forward_signal_snapshots")}
    previous = {r["canonical_signal_id"]: json.loads(r["payload_json"]) for r in store.list_canonical_outcomes(limit=-1)}
    signals = store.list_canonical_signals(limit=-1)
    classes = {}
    for c in store.validation_records("forward_signal_classifications"):
        classes.setdefault(c["canonical_signal_id"], []).append(c)
    cache, updated, skipped = {}, 0, 0
    def bars_for(ticker):
        if ticker not in cache:
            cache[ticker] = db.fetch_candles(ticker, "1d", limit=-1) if db else []
        return cache[ticker]
    for sig in signals:
        cid = sig["canonical_signal_id"]
        snap = forwards.get(cid)
        if forward_validation_only and (not snap or not eligible_sample(snap)):
            continue
        old = previous.get(cid) or {}
        if snap and old.get("source_cutoff_timestamp") != snap.get("source_cutoff_timestamp"):
            old = {}
        if pending_only and all(old.get(f"maturity_{h}") == "MATURE" for h in horizons):
            skipped += 1
            continue
        if snap:
            effective = dict(snap)
            future = sessions_after([b for b in bars_for(sig["ticker"]) if (_session_key(b) or "") <= through], snap.get("outcome_after_session"))
            context = {"session_dates": [_session_key(b) for b in future]}
            for c in sorted(classes.get(cid, []), key=lambda r: parse_dt(r["analysis_imported_at"])):
                if _class_known_before_outcome(c, context, snap):
                    for key, source_key in (("target_price_t0", "target_source"), ("stop_or_invalidation_t0", "stop_source")):
                        if effective.get(key) is None and c["fields"].get(key) is not None:
                            effective[key] = c["fields"][key]
                            effective[source_key] = c["fields"].get(source_key) or c["classification_source"]
            rec = outcome_for_snapshot(effective, bars_for(sig["ticker"]), horizons=horizons, through_session=through)
            rec["target_stop_definition"] = {k: effective.get(k) for k in ("target_price_t0", "stop_or_invalidation_t0", "target_source", "stop_source")}
        else:
            payload = sig.get("payload") or {}
            rec = compute_outcomes(baseline_price=sig.get("price_at_signal"),
                baseline_timestamp=payload.get("price_timestamp") or sig.get("signal_timestamp"),
                baseline_type=sig.get("price_observation_type") or "OFFICIAL_CLOSE",
                signal_session=sig.get("market_session_basis"),
                future_bars=[b for b in bars_for(sig["ticker"]) if (_session_key(b) or "") <= through and b.get("is_complete") is not False],
                history_integrity=payload.get("TECHNICAL_HISTORY_INTEGRITY"), horizons=horizons)
        rec.update({"canonical_signal_id": cid, "ticker": sig["ticker"], "scanner_unit": "canonical_signal_id"})
        # A bounded rerun cannot erase already mature horizons or optional +60 evidence.
        rec = preserve_maturity(old, rec)
        if not dry_run and rec != old:
            store.upsert_canonical_outcome(rec)
            if sig.get("origin_snapshot_id"):
                store.upsert_signal_outcome({**rec, "snapshot_id": sig["origin_snapshot_id"]})
        updated += 1
    universe_updated = 0
    prior_members = {r["record_id"]: r for r in store.validation_records("universe_member_outcomes")}
    for member in store.validation_records("universe_snapshot_members"):
        if forward_validation_only and not eligible_sample(member):
            continue
        key = member["record_id"]
        old = prior_members.get(key) or {}
        if pending_only and all(old.get(f"maturity_{h}") == "MATURE" for h in horizons):
            continue
        rec = outcome_for_snapshot(member, bars_for(member["ticker"]), horizons=horizons, through_session=through)
        rec["universe_snapshot_id"] = member["universe_snapshot_id"]
        rec = preserve_maturity(old, rec)
        if not dry_run:
            store.upsert_universe_outcome(key, rec)
        universe_updated += 1
    return {"updated": updated, "universe_updated": universe_updated, "skipped": skipped,
            "dry_run": dry_run, "pending_only": pending_only, "through_session": through,
            "horizons": list(horizons), "scanner_sample_n": len(forwards) if forward_validation_only else len(signals),
            "note": "T0 and scanner 0.5.1 stay unchanged. Outcomes require completed future trading sessions."}


def preserve_maturity(old: dict, new: dict) -> dict:
    merged = {**old, **new}
    for h in (1, 2, 3, 5, 10, 20, 60):
        if old.get(f"maturity_{h}") == "MATURE":
            for key, value in old.items():
                if key.endswith(f"_{h}") or key == f"return_{h}_sessions":
                    merged[key] = value
    if (old.get("sessions_available") or 0) > (new.get("sessions_available") or 0):
        for key in ("sessions_available", "session_dates", "through_session", "outcome_status", "horizons_complete", "next_session_return"):
            if key in old:
                merged[key] = old[key]
    return merged
