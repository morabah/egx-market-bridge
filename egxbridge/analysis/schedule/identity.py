"""Canonical market-signal identity — calibration integrity without score retuning.

One Explorer candidate setup at a defined point-in-time market state has one
canonical_signal_id. Schedule jobs are analysis observations of that signal.

Identity layers (do not mix):
- process_identity: explorer_run_id, schedule_run_id, package timestamps
- market_state_identity: market_state_fingerprint → canonical_signal_id
- analysis_observation_identity: analysis_observation_id

explorer_run_id is provenance. It does not mint a new scanner signal.

Numeric fingerprint normalization:
- prices, percent returns, RVOL, distances: round to 4 decimal places, then
  format as exactly 4 digits after the decimal (e.g. 2.5 → "2.5000")
- booleans: "0" / "1"
- missing: empty string
- SMA relationship: ABOVE / BELOW / EQUAL (never raw SMA floats)
- enums: uppercase
Wall-clock packaging seconds are never hashed.
"""
from __future__ import annotations

from typing import Any
import hashlib

from egxbridge.analysis.explorer.calibration import SCORING_VERSION
from egxbridge.analysis.schedule.session import parse_dt, CAIRO
from egxbridge.analysis.schedule.types import (
    ANALYSIS_EXPLORER, ANALYSIS_INTRADAY, ANALYSIS_TYPES,
    LAYER_LOCAL_SIGNAL, LAYER_CHATGPT_ANALYSIS,
)


ORIGIN_EXPLORER = "EXPLORER"
ORIGIN_INTRADAY = "INTRADAY"

LIVE_PHASES = {"CONTINUOUS_TRADING", "CLOSING_AUCTION", "TRADING_AT_LAST"}
INTRADAY_BUCKET_MINUTES = 20
FINGERPRINT_QUANTIZE_DP = 4


def _sha(*parts: Any) -> str:
    raw = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def quantize(value: Any, ndigits: int = FINGERPRINT_QUANTIZE_DP) -> str:
    """Canonical numeric string. Prevents float repr churn in hashes."""
    if value is None or value == "":
        return ""
    try:
        return f"{round(float(value), ndigits):.{ndigits}f}"
    except Exception:
        return ""


def price_fingerprint(price: Any) -> str:
    return quantize(price, FINGERPRINT_QUANTIZE_DP)


def _flag(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    s = str(value).strip().lower()
    if s in {"1", "true", "yes"}:
        return "1"
    if s in {"0", "false", "no"}:
        return "0"
    return str(value).strip().upper()


def _enum(value: Any) -> str:
    if value is None or value == "":
        return ""
    return str(value).strip().upper()


def _pick(candidate: dict[str, Any], *keys: str) -> Any:
    m = candidate.get("metrics") if isinstance(candidate.get("metrics"), dict) else {}
    struct = candidate.get("structure") if isinstance(candidate.get("structure"), dict) else {}
    for k in keys:
        if candidate.get(k) is not None and candidate.get(k) != "":
            return candidate.get(k)
        if m.get(k) is not None and m.get(k) != "":
            return m.get(k)
        if struct.get(k) is not None and struct.get(k) != "":
            return struct.get(k)
    return None


def _sma_rel(close: Any, sma: Any, explicit: Any = None) -> str:
    if explicit:
        s = str(explicit).upper()
        if "ABOVE" in s:
            return "ABOVE"
        if "BELOW" in s:
            return "BELOW"
        if "EQUAL" in s:
            return "EQUAL"
    c, s = quantize(close), quantize(sma)
    if not c or not s:
        return ""
    if c > s:
        return "ABOVE"
    if c < s:
        return "BELOW"
    return "EQUAL"


def make_explorer_run_id(
    *,
    environment: str,
    latest_session: str | None,
    generated_at: str | None,
    scoring_version: str = SCORING_VERSION,
) -> str:
    """Process identity of one Explorer package. Not market-state identity."""
    return "xr_" + _sha(environment, latest_session or "", generated_at or "", scoring_version)[:24]


def signal_family_id(
    *,
    environment: str,
    ticker: str,
    explorer_run_id: str | None = None,
    market_session_basis: str | None,
) -> str:
    """Family groups official-close + later intraday children of the same session.

    explorer_run_id is ignored: process identity must not split a family.
    """
    _ = explorer_run_id
    return "fam_" + _sha(
        environment or "",
        str(ticker or "").upper(),
        market_session_basis or "",
    )[:24]


def market_state_fingerprint(
    candidate: dict[str, Any] | None,
    *,
    environment: str,
    ticker: str,
    market_session_basis: str | None,
    scoring_version: str,
    signal_origin: str,
    price_observation_type: str | None = "OFFICIAL_CLOSE",
    intraday_state_bucket: str | None = "",
) -> str:
    """Hash of material market evidence. Not a package or process id.

    Non-live / official-close: daily session evidence.
    Live / intraday: price fingerprint + data timestamp. A new Cairo bucket
    is recorded as metadata but is NOT hashed unless price/structure evidence
    is present (bucket-alone never mints a new signal).
    """
    c = candidate or {}
    origin = signal_origin or ORIGIN_EXPLORER
    close = _pick(c, "last_close", "latest_close", "price_at_signal", "price_at_snapshot")
    daily = _pick(c, "daily_return_pct", "daily_return")
    rvol = _pick(c, "rvol_20", "RVOL20")
    d20 = _pick(c, "dist_from_20d_high_pct", "distance_20d_high")
    d60 = _pick(c, "dist_from_60d_high_pct", "distance_60d_high")
    sma20 = _pick(c, "sma_20")
    sma50 = _pick(c, "sma_50")
    rel20 = _sma_rel(close, sma20, _pick(c, "above_or_below_SMA20"))
    rel50 = _sma_rel(close, sma50, _pick(c, "above_or_below_SMA50"))
    b20 = _flag(_pick(c, "breakout_20d", "breakout_flag_20d"))
    b60 = _flag(_pick(c, "breakout_60d", "breakout_flag_60d"))
    quality = _enum(_pick(c, "FORWARD_SETUP_QUALITY"))
    realized = _enum(_pick(c, "MOVE_ALREADY_REALIZED"))
    lane = _enum(_pick(c, "candidate_lane"))
    px_ts = _pick(
        c, "latest_normalized_timestamp", "price_timestamp",
        "latest_completed_market_session", "latest_session", "session_date",
    )
    data_cutoff = _pick(c, "data_cutoff_id", "normalized_source_id")
    parts = [
        "msv1",
        environment or "",
        str(ticker or "").upper(),
        market_session_basis or "",
        scoring_version or SCORING_VERSION,
        origin,
        quantize(close),
        quantize(daily),
        quantize(rvol),
        quantize(d20),
        quantize(d60),
        rel20,
        rel50,
        b20,
        b60,
        quality,
        realized,
        lane,
        str(px_ts or ""),
        str(data_cutoff or ""),
    ]
    if origin == ORIGIN_INTRADAY:
        live_px = (
            _pick(c, "current_session_price", "price_at_snapshot")
            or (c.get("intraday") or {}).get("current_session_price")
            or (c.get("intraday") or {}).get("last_price")
            or close
        )
        live_ts = _pick(c, "intraday_price_timestamp", "normalized_intraday_timestamp") or ""
        # Cairo bucket is metadata only. Clock-bucket changes without a new price
        # timestamp or price fingerprint must not mint a new canonical.
        parts.extend([
            price_observation_type or "CURRENT_INTRADAY_PRICE",
            price_fingerprint(live_px),
            str(live_ts),
        ])
    else:
        parts.extend(["OFFICIAL_CLOSE", "", "", ""])
    return "ms_" + _sha(*parts)[:40]


def canonical_signal_id(
    *,
    environment: str,
    ticker: str,
    market_session_basis: str | None,
    scoring_version: str,
    explorer_run_id: str | None = None,
    signal_origin: str,
    price_observation_type: str | None = "OFFICIAL_CLOSE",
    price_fingerprint_value: str = "",
    intraday_state_bucket: str | None = "",
    market_state_fingerprint_value: str | None = None,
    candidate: dict[str, Any] | None = None,
) -> str:
    """Hash of point-in-time *market* state. explorer_run_id is not used."""
    _ = explorer_run_id
    _ = price_fingerprint_value
    origin = signal_origin or ORIGIN_EXPLORER
    fp = market_state_fingerprint_value or market_state_fingerprint(
        candidate,
        environment=environment,
        ticker=ticker,
        market_session_basis=market_session_basis,
        scoring_version=scoring_version,
        signal_origin=origin,
        price_observation_type=price_observation_type,
        intraday_state_bucket=intraday_state_bucket,
    )
    return _sha(
        environment or "",
        str(ticker or "").upper(),
        market_session_basis or "",
        scoring_version or SCORING_VERSION,
        origin,
        fp,
        "OFFICIAL_CLOSE" if origin != ORIGIN_INTRADAY else (price_observation_type or "CURRENT_INTRADAY_PRICE"),
    )


def analysis_observation_id(
    *,
    canonical_id: str,
    analysis_type: str,
    schedule_run_id: str | None,
    generated_by: str = "LOCAL",
) -> str:
    """Provenance of one analysis look. May be unique per package run."""
    return "ao_" + _sha(
        canonical_id or "",
        analysis_type or "",
        schedule_run_id or "",
        generated_by or "LOCAL",
    )[:40]


def intraday_state_bucket(
    session_meta: dict[str, Any] | None,
    *,
    has_current_session_evidence: bool,
    bucket_minutes: int | None = None,
) -> str | None:
    """Cairo bucket during live session. Metadata only unless paired with new prices."""
    if not has_current_session_evidence:
        return None
    sess = session_meta or {}
    phase = sess.get("session_phase")
    if phase not in LIVE_PHASES:
        return None
    cairo_ts = sess.get("analysis_timestamp_cairo") or sess.get("analysis_timestamp_utc")
    dt = parse_dt(cairo_ts) if cairo_ts else None
    if dt is None:
        return None
    cairo = dt.astimezone(CAIRO)
    step = int(bucket_minutes or sess.get("intraday_bucket_minutes") or INTRADAY_BUCKET_MINUTES)
    if step <= 0:
        step = INTRADAY_BUCKET_MINUTES
    minute = (cairo.minute // step) * step
    return f"{cairo.hour:02d}:{minute:02d}"


def has_current_session_evidence(candidate: dict[str, Any], *, price_basis: str | None = None) -> bool:
    if (price_basis or candidate.get("price_observation_type")) == "CURRENT_INTRADAY_PRICE":
        return True
    intra = candidate.get("intraday") or {}
    if isinstance(intra, dict):
        if intra.get("current_session_price") is not None or intra.get("last_price") is not None:
            return True
        if intra.get("intraday_available") and intra.get("current_session"):
            return True
        rows = intra.get("interval_rows") or intra.get("rows") or []
        if any(isinstance(r, dict) and r.get("available") and r.get("current_session") for r in rows):
            return True
    if candidate.get("current_session_price") is not None:
        return True
    return False


def explorer_canonical_id(
    *,
    environment: str,
    ticker: str,
    market_session_basis: str | None,
    explorer_run_id: str | None = None,
    scoring_version: str = SCORING_VERSION,
    candidate: dict[str, Any] | None = None,
) -> str:
    """Official-close canonical id. explorer_run_id is provenance only."""
    row = dict(candidate or {})
    row.setdefault("ticker", ticker)
    fp = market_state_fingerprint(
        row,
        environment=environment,
        ticker=ticker,
        market_session_basis=market_session_basis,
        scoring_version=scoring_version,
        signal_origin=ORIGIN_EXPLORER,
        price_observation_type="OFFICIAL_CLOSE",
    )
    return canonical_signal_id(
        environment=environment,
        ticker=ticker,
        market_session_basis=market_session_basis,
        scoring_version=scoring_version,
        explorer_run_id=explorer_run_id,
        signal_origin=ORIGIN_EXPLORER,
        price_observation_type="OFFICIAL_CLOSE",
        market_state_fingerprint_value=fp,
        candidate=row,
    )


def should_open_intraday_child(
    *,
    analysis_type: str | None,
    price_basis: str | None,
    candidate: dict[str, Any],
    session_meta: dict[str, Any] | None,
) -> bool:
    """New canonical only for a live-session observation with new market evidence."""
    if analysis_type != ANALYSIS_INTRADAY:
        return False
    if (price_basis or "") not in {"CURRENT_INTRADAY_PRICE", "BAR_CLOSE"}:
        if not has_current_session_evidence(candidate, price_basis=price_basis):
            return False
        if (price_basis or "OFFICIAL_CLOSE") == "OFFICIAL_CLOSE":
            return False
    if not (
        has_current_session_evidence(candidate, price_basis=price_basis)
        or (
            price_basis in {"CURRENT_INTRADAY_PRICE", "BAR_CLOSE"}
            and (session_meta or {}).get("session_phase") in LIVE_PHASES
        )
    ):
        return False
    live_px = (
        candidate.get("current_session_price")
        or (candidate.get("intraday") or {}).get("current_session_price")
        or (candidate.get("intraday") or {}).get("last_price")
    )
    close = _pick(candidate, "last_close", "latest_close")
    if live_px is None:
        return False
    # Same printed price as official close is not new market evidence.
    if close is not None and price_fingerprint(live_px) == price_fingerprint(close):
        return False
    return True


def resolve_signal_identity(
    candidate: dict[str, Any],
    *,
    environment: str,
    explorer_run_id: str | None,
    latest_session: str | None,
    analysis_type: str | None = None,
    session_meta: dict[str, Any] | None = None,
    price_basis: str = "OFFICIAL_CLOSE",
    scoring_version: str = SCORING_VERSION,
) -> dict[str, Any]:
    """Return identity fields. Process ids are not a new-signal proof."""
    ticker = str(candidate.get("ticker") or "").upper()
    session_basis = (
        candidate.get("latest_completed_market_session")
        or latest_session
    )
    family = signal_family_id(
        environment=environment,
        ticker=ticker,
        explorer_run_id=explorer_run_id,
        market_session_basis=session_basis,
    )
    parent_fp = market_state_fingerprint(
        candidate,
        environment=environment,
        ticker=ticker,
        market_session_basis=session_basis,
        scoring_version=scoring_version,
        signal_origin=ORIGIN_EXPLORER,
        price_observation_type="OFFICIAL_CLOSE",
    )
    parent_id = canonical_signal_id(
        environment=environment,
        ticker=ticker,
        market_session_basis=session_basis,
        scoring_version=scoring_version,
        explorer_run_id=explorer_run_id,
        signal_origin=ORIGIN_EXPLORER,
        market_state_fingerprint_value=parent_fp,
        candidate=candidate,
    )
    open_child = should_open_intraday_child(
        analysis_type=analysis_type,
        price_basis=price_basis,
        candidate=candidate,
        session_meta=session_meta,
    )
    if not open_child:
        return {
            "canonical_signal_id": parent_id,
            "market_state_fingerprint": parent_fp,
            "signal_family_id": family,
            "parent_signal_id": None,
            "signal_origin": ORIGIN_EXPLORER,
            "intraday_state_bucket": None,
            "price_observation_type": price_basis or "OFFICIAL_CLOSE",
            "explorer_run_id": explorer_run_id,
            "market_session_basis": session_basis,
            "is_new_market_state": False,
            "process_identity": explorer_run_id,
            "market_state_identity": parent_fp,
        }

    m = candidate.get("metrics") or candidate
    price = (
        candidate.get("current_session_price")
        or candidate.get("price_at_snapshot")
        or (candidate.get("intraday") or {}).get("current_session_price")
        or (candidate.get("intraday") or {}).get("last_price")
        or candidate.get("last_close")
        or m.get("last_close")
    )
    bucket = intraday_state_bucket(session_meta, has_current_session_evidence=True)
    child_fp = market_state_fingerprint(
        candidate,
        environment=environment,
        ticker=ticker,
        market_session_basis=session_basis,
        scoring_version=scoring_version,
        signal_origin=ORIGIN_INTRADAY,
        price_observation_type=price_basis or "CURRENT_INTRADAY_PRICE",
        intraday_state_bucket=bucket,
    )
    child_id = canonical_signal_id(
        environment=environment,
        ticker=ticker,
        market_session_basis=session_basis,
        scoring_version=scoring_version,
        explorer_run_id=explorer_run_id,
        signal_origin=ORIGIN_INTRADAY,
        price_observation_type=price_basis or "CURRENT_INTRADAY_PRICE",
        price_fingerprint_value=price_fingerprint(price),
        intraday_state_bucket=bucket,
        market_state_fingerprint_value=child_fp,
        candidate=candidate,
    )
    return {
        "canonical_signal_id": child_id,
        "market_state_fingerprint": child_fp,
        "signal_family_id": family,
        "parent_signal_id": None if child_id == parent_id else parent_id,
        "signal_origin": ORIGIN_INTRADAY,
        "intraday_state_bucket": bucket,
        "price_observation_type": price_basis or "CURRENT_INTRADAY_PRICE",
        "explorer_run_id": explorer_run_id,
        "market_session_basis": session_basis,
        "is_new_market_state": child_id != parent_id,
        "process_identity": explorer_run_id,
        "market_state_identity": child_fp,
    }


def canonical_record_from_candidate(
    candidate: dict[str, Any],
    *,
    identity: dict[str, Any],
    environment: str,
    scoring_version: str = SCORING_VERSION,
    origin_snapshot_id: str | None = None,
    signal_timestamp: str | None = None,
) -> dict[str, Any]:
    m = candidate.get("metrics") or candidate
    price = (
        candidate.get("price_at_snapshot")
        or candidate.get("price_at_signal")
        or candidate.get("last_close")
        or m.get("last_close")
    )
    if identity.get("signal_origin") == ORIGIN_INTRADAY:
        price = (
            candidate.get("current_session_price")
            or (candidate.get("intraday") or {}).get("current_session_price")
            or (candidate.get("intraday") or {}).get("last_price")
            or price
        )
    xr = identity.get("explorer_run_id")
    return {
        "canonical_signal_id": identity["canonical_signal_id"],
        "market_state_fingerprint": identity.get("market_state_fingerprint"),
        "ticker": str(candidate.get("ticker") or "").upper(),
        "environment": environment,
        "market_session_basis": identity.get("market_session_basis"),
        "signal_timestamp": signal_timestamp,
        "signal_origin": identity.get("signal_origin"),
        "scoring_version": scoring_version,
        "explorer_run_id": xr,
        "first_explorer_run_id": xr,
        "latest_seen_explorer_run_id": xr,
        "candidate_rank": candidate.get("calibrated_rank") or candidate.get("candidate_rank"),
        "candidate_lane": candidate.get("candidate_lane"),
        "FORWARD_SETUP_QUALITY": candidate.get("FORWARD_SETUP_QUALITY"),
        "MOVE_ALREADY_REALIZED": candidate.get("MOVE_ALREADY_REALIZED"),
        "candidate_score_calibrated": candidate.get("candidate_score_calibrated") or candidate.get("candidate_score"),
        "price_at_signal": price,
        "price_observation_type": identity.get("price_observation_type"),
        "session_phase": (identity.get("session_phase") if "session_phase" in identity else None),
        "parent_signal_id": identity.get("parent_signal_id"),
        "signal_family_id": identity.get("signal_family_id"),
        "intraday_state_bucket": identity.get("intraday_state_bucket"),
        "origin_snapshot_id": origin_snapshot_id,
        "TECHNICAL_HISTORY_INTEGRITY": candidate.get("TECHNICAL_HISTORY_INTEGRITY"),
        "layer": LAYER_LOCAL_SIGNAL,
        "not_a_probability": True,
    }


def observation_record(
    *,
    identity: dict[str, Any],
    analysis_type: str,
    ticker: str,
    environment: str,
    analysis_timestamp: str | None,
    schedule_run_id: str | None,
    generated_by: str = "LOCAL",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    oid = analysis_observation_id(
        canonical_id=identity["canonical_signal_id"],
        analysis_type=analysis_type,
        schedule_run_id=schedule_run_id,
        generated_by=generated_by,
    )
    rec = {
        "analysis_observation_id": oid,
        "canonical_signal_id": identity["canonical_signal_id"],
        "analysis_type": analysis_type,
        "analysis_timestamp": analysis_timestamp,
        "schedule_run_id": schedule_run_id,
        "explorer_run_id": identity.get("explorer_run_id"),
        "ticker": str(ticker or "").upper(),
        "generated_by": generated_by,
        "environment": environment,
        "layer": LAYER_CHATGPT_ANALYSIS if generated_by == "CHATGPT_HANDOFF" else "ANALYSIS_OBSERVATION",
        "signal_origin": identity.get("signal_origin"),
        "parent_signal_id": identity.get("parent_signal_id"),
        "signal_family_id": identity.get("signal_family_id"),
        "market_state_fingerprint": identity.get("market_state_fingerprint"),
        "import_status": "IMPORTED" if generated_by == "CHATGPT_HANDOFF" else "GENERATED",
        "linkage_method": extra.get("linkage_method") if extra else None,
    }
    if extra:
        rec.update(extra)
    if generated_by == "LOCAL" and not rec.get("import_status"):
        rec["import_status"] = "GENERATED"
    return rec


def persist_identity_for_snapshots(
    store,
    snapshots: list[dict[str, Any]],
    *,
    analysis_type: str = ANALYSIS_EXPLORER,
    schedule_run_id: str | None = None,
    generated_by: str = "LOCAL",
) -> dict[str, Any]:
    """Attach canonical signals + observations. Never mutates snapshot payload rows."""
    inserted_c = 0
    reused_c = 0
    inserted_o = 0
    ids = []
    obs_ids = []
    if store is None:
        return {
            "canonical_inserted": 0, "canonical_reused": 0,
            "observations_inserted": 0, "canonical_ids": [], "observation_ids": [],
        }
    for snap in snapshots:
        ident = {
            "canonical_signal_id": snap.get("canonical_signal_id"),
            "market_state_fingerprint": snap.get("market_state_fingerprint"),
            "signal_family_id": snap.get("signal_family_id"),
            "parent_signal_id": snap.get("parent_signal_id"),
            "signal_origin": snap.get("signal_origin") or ORIGIN_EXPLORER,
            "explorer_run_id": snap.get("explorer_run_id"),
            "market_session_basis": snap.get("latest_completed_market_session") or snap.get("market_session_basis"),
            "price_observation_type": snap.get("price_observation_type") or "OFFICIAL_CLOSE",
            "intraday_state_bucket": snap.get("intraday_state_bucket"),
            "session_phase": snap.get("session_phase"),
        }
        rec = {
            "canonical_signal_id": ident["canonical_signal_id"],
            "market_state_fingerprint": ident.get("market_state_fingerprint"),
            "ticker": snap.get("ticker"),
            "environment": snap.get("environment") or getattr(store, "environment", None),
            "market_session_basis": ident["market_session_basis"],
            "signal_timestamp": snap.get("analysis_timestamp_utc") or snap.get("package_generated_at"),
            "signal_origin": ident["signal_origin"],
            "scoring_version": snap.get("scoring_version") or SCORING_VERSION,
            "explorer_run_id": ident["explorer_run_id"],
            "first_explorer_run_id": ident["explorer_run_id"],
            "latest_seen_explorer_run_id": ident["explorer_run_id"],
            "candidate_rank": snap.get("calibrated_rank") or snap.get("candidate_rank"),
            "candidate_lane": snap.get("candidate_lane"),
            "FORWARD_SETUP_QUALITY": snap.get("FORWARD_SETUP_QUALITY"),
            "MOVE_ALREADY_REALIZED": snap.get("MOVE_ALREADY_REALIZED"),
            "candidate_score_calibrated": snap.get("candidate_score_calibrated"),
            "price_at_signal": snap.get("price_at_snapshot") or snap.get("price_at_signal"),
            "price_observation_type": ident["price_observation_type"],
            "session_phase": snap.get("session_phase"),
            "parent_signal_id": ident["parent_signal_id"],
            "signal_family_id": ident["signal_family_id"],
            "intraday_state_bucket": ident.get("intraday_state_bucket"),
            "origin_snapshot_id": snap.get("snapshot_id"),
            "TECHNICAL_HISTORY_INTEGRITY": snap.get("TECHNICAL_HISTORY_INTEGRITY"),
            "layer": LAYER_LOCAL_SIGNAL,
            "not_a_probability": True,
        }
        cid, new = store.insert_canonical_signal(rec)
        ident["canonical_signal_id"] = cid
        ids.append(cid)
        if new:
            inserted_c += 1
        else:
            reused_c += 1
        obs = observation_record(
            identity=ident,
            analysis_type=analysis_type or snap.get("analysis_type") or ANALYSIS_EXPLORER,
            ticker=snap.get("ticker") or "",
            environment=rec["environment"],
            analysis_timestamp=snap.get("analysis_timestamp_utc") or snap.get("package_generated_at"),
            schedule_run_id=schedule_run_id or snap.get("run_id"),
            generated_by=generated_by,
            extra={"origin_snapshot_id": snap.get("snapshot_id"), "import_status": "GENERATED"},
        )
        oid, onew = store.insert_analysis_observation(obs)
        obs_ids.append(oid)
        if onew:
            inserted_o += 1
    return {
        "canonical_inserted": inserted_c,
        "canonical_reused": reused_c,
        "observations_inserted": inserted_o,
        "canonical_ids": ids,
        "observation_ids": obs_ids,
        "canonical_signals_n": len(set(ids)),
        "analysis_observations_n": len(obs_ids),
        "analysis_observations_generated_n": len(obs_ids),
    }


def persist_job_observations(
    store,
    *,
    candidates: list[dict[str, Any]],
    jobs: list[str],
    environment: str,
    explorer_run_id: str | None,
    latest_session: str | None,
    schedule_run_id: str | None,
    analysis_timestamp: str | None,
    session_meta: dict[str, Any] | None,
) -> dict[str, Any]:
    """One observation per job per ticker. Reuses canonical signals. No score change."""
    inserted_c = reused_c = inserted_o = 0
    canonical_ids = []
    obs_ids = []
    by_ticker: dict[str, str] = {}
    by_ticker_identity: dict[str, dict[str, Any]] = {}
    identities_by_job: dict[str, dict[str, dict[str, Any]]] = {j: {} for j in jobs}
    if store is None:
        return {
            "canonical_inserted": 0, "canonical_reused": 0, "observations_inserted": 0,
            "canonical_ids": [], "observation_ids": [], "by_ticker": {},
            "canonical_signals_n": 0, "analysis_observations_n": 0,
            "analysis_observations_generated_n": 0,
            "by_ticker_identity": {}, "identities_by_job": identities_by_job,
        }
    for c in candidates:
        ticker = str(c.get("ticker") or "").upper()
        ident = resolve_signal_identity(
            c,
            environment=environment,
            explorer_run_id=explorer_run_id,
            latest_session=latest_session,
            analysis_type=ANALYSIS_EXPLORER,
            session_meta=session_meta,
            price_basis="OFFICIAL_CLOSE",
        )
        rec = canonical_record_from_candidate(
            c, identity=ident, environment=environment,
            signal_timestamp=analysis_timestamp,
        )
        rec["session_phase"] = (session_meta or {}).get("session_phase")
        cid, new = store.insert_canonical_signal(rec)
        ident["canonical_signal_id"] = cid
        canonical_ids.append(cid)
        by_ticker[ticker] = cid
        by_ticker_identity[ticker] = dict(ident)
        if new:
            inserted_c += 1
        else:
            reused_c += 1
        for job in jobs:
            if job not in ANALYSIS_TYPES and job != ANALYSIS_EXPLORER:
                continue
            job_ident = dict(ident)
            if job == ANALYSIS_INTRADAY and should_open_intraday_child(
                analysis_type=job,
                price_basis="CURRENT_INTRADAY_PRICE" if has_current_session_evidence(c) else "OFFICIAL_CLOSE",
                candidate=c,
                session_meta=session_meta,
            ):
                job_ident = resolve_signal_identity(
                    c,
                    environment=environment,
                    explorer_run_id=explorer_run_id,
                    latest_session=latest_session,
                    analysis_type=ANALYSIS_INTRADAY,
                    session_meta=session_meta,
                    price_basis="CURRENT_INTRADAY_PRICE",
                )
                child = canonical_record_from_candidate(
                    c, identity=job_ident, environment=environment,
                    signal_timestamp=analysis_timestamp,
                )
                child["session_phase"] = (session_meta or {}).get("session_phase")
                ccid, cnew = store.insert_canonical_signal(child)
                job_ident["canonical_signal_id"] = ccid
                canonical_ids.append(ccid)
                if cnew:
                    inserted_c += 1
                else:
                    reused_c += 1
            identities_by_job.setdefault(job, {})[ticker] = dict(job_ident)
            obs = observation_record(
                identity=job_ident,
                analysis_type=job,
                ticker=ticker,
                environment=environment,
                analysis_timestamp=analysis_timestamp,
                schedule_run_id=schedule_run_id,
                generated_by="LOCAL",
                extra={"import_status": "GENERATED", "linkage_method": None},
            )
            oid, onew = store.insert_analysis_observation(obs)
            obs_ids.append(oid)
            if onew:
                inserted_o += 1
    unique_c = list(dict.fromkeys(canonical_ids))
    return {
        "canonical_inserted": inserted_c,
        "canonical_reused": reused_c,
        "observations_inserted": inserted_o,
        "canonical_ids": unique_c,
        "observation_ids": obs_ids,
        "by_ticker": by_ticker,
        "by_ticker_identity": by_ticker_identity,
        "identities_by_job": identities_by_job,
        "canonical_signals_n": len(unique_c),
        "analysis_observations_n": len(obs_ids),
        "analysis_observations_generated_n": len(obs_ids),
        "scanner_sample_n": len(unique_c),
        "note": "Scanner sample size is canonical_signals_n, not analysis_observations_generated_n",
    }


def backfill_canonical_from_legacy_snapshots(store) -> dict[str, Any]:
    """Non-destructive: group existing snapshots into canonical signals. No outcomes written."""
    if store is None:
        return {"inserted": 0, "linked": 0}
    existing = store.list_canonical_signals(limit=1)
    if existing:
        return {"inserted": 0, "linked": 0, "skipped": "canonical_table_already_populated"}
    snaps = store.list_signal_snapshots(limit=5000)
    inserted = 0
    linked = 0
    groups: dict[tuple, list] = {}
    for s in snaps:
        p = s.get("payload") or s
        ticker = (s.get("ticker") or p.get("ticker") or "").upper()
        session = s.get("latest_completed_market_session") or p.get("latest_completed_market_session")
        scoring = s.get("scoring_version") or p.get("scoring_version") or SCORING_VERSION
        env = s.get("environment") or getattr(store, "environment", "")
        px = p.get("price_observation_type") or "OFFICIAL_CLOSE"
        origin = p.get("signal_origin") or ORIGIN_EXPLORER
        if origin == ORIGIN_INTRADAY or px in {"CURRENT_INTRADAY_PRICE", "BAR_CLOSE"}:
            key = ("intra", env, ticker, session, scoring, px, price_fingerprint(p.get("price_at_snapshot")), p.get("intraday_state_bucket") or "")
        else:
            key = ("scan", env, ticker, session, scoring, "OFFICIAL_CLOSE")
        groups.setdefault(key, []).append(s)

    for key, members in groups.items():
        members_sorted = sorted(members, key=lambda r: r.get("id") or 0)
        origin_snap = next(
            (m for m in members_sorted if (m.get("analysis_type") or (m.get("payload") or {}).get("analysis_type")) == ANALYSIS_EXPLORER),
            members_sorted[0],
        )
        p = origin_snap.get("payload") or origin_snap
        env = origin_snap.get("environment") or getattr(store, "environment", "")
        ticker = (origin_snap.get("ticker") or p.get("ticker") or "").upper()
        session = origin_snap.get("latest_completed_market_session") or p.get("latest_completed_market_session")
        xr = p.get("explorer_run_id")
        if not xr:
            xr = make_explorer_run_id(
                environment=env,
                latest_session=session,
                generated_at=str(session or "") + "|legacy|" + ticker,
            )
        kind = key[0]
        cand = {
            "ticker": ticker,
            "last_close": p.get("price_at_snapshot"),
            "FORWARD_SETUP_QUALITY": p.get("FORWARD_SETUP_QUALITY"),
            "MOVE_ALREADY_REALIZED": p.get("MOVE_ALREADY_REALIZED"),
            "candidate_lane": p.get("candidate_lane"),
            "rvol_20": p.get("RVOL20"),
            "dist_from_20d_high_pct": p.get("distance_20d_high"),
            "dist_from_60d_high_pct": p.get("distance_60d_high"),
            "breakout_20d": p.get("breakout_20d"),
            "breakout_60d": p.get("breakout_60d"),
        }
        if kind == "intra":
            ident_origin = ORIGIN_INTRADAY
            cand["current_session_price"] = p.get("price_at_snapshot")
            fp = market_state_fingerprint(
                cand, environment=env, ticker=ticker, market_session_basis=session,
                scoring_version=p.get("scoring_version") or SCORING_VERSION,
                signal_origin=ORIGIN_INTRADAY,
                price_observation_type=p.get("price_observation_type") or "CURRENT_INTRADAY_PRICE",
                intraday_state_bucket=p.get("intraday_state_bucket") or "",
            )
            cid = canonical_signal_id(
                environment=env, ticker=ticker, market_session_basis=session,
                scoring_version=p.get("scoring_version") or SCORING_VERSION,
                explorer_run_id=xr, signal_origin=ORIGIN_INTRADAY,
                price_observation_type=p.get("price_observation_type") or "CURRENT_INTRADAY_PRICE",
                market_state_fingerprint_value=fp, candidate=cand,
            )
            parent = explorer_canonical_id(
                environment=env, ticker=ticker, market_session_basis=session,
                explorer_run_id=xr, candidate=cand,
            )
        else:
            ident_origin = ORIGIN_EXPLORER
            fp = market_state_fingerprint(
                cand, environment=env, ticker=ticker, market_session_basis=session,
                scoring_version=p.get("scoring_version") or SCORING_VERSION,
                signal_origin=ORIGIN_EXPLORER,
            )
            cid = explorer_canonical_id(
                environment=env, ticker=ticker, market_session_basis=session,
                explorer_run_id=xr, candidate=cand,
            )
            parent = None
        rec = {
            "canonical_signal_id": cid,
            "market_state_fingerprint": fp,
            "ticker": ticker,
            "environment": env,
            "market_session_basis": session,
            "signal_timestamp": origin_snap.get("analysis_timestamp_utc") or p.get("analysis_timestamp_utc"),
            "signal_origin": ident_origin,
            "scoring_version": p.get("scoring_version") or SCORING_VERSION,
            "explorer_run_id": xr,
            "first_explorer_run_id": xr,
            "latest_seen_explorer_run_id": xr,
            "candidate_rank": p.get("calibrated_rank") or p.get("candidate_rank"),
            "candidate_lane": p.get("candidate_lane"),
            "FORWARD_SETUP_QUALITY": p.get("FORWARD_SETUP_QUALITY"),
            "MOVE_ALREADY_REALIZED": p.get("MOVE_ALREADY_REALIZED"),
            "candidate_score_calibrated": p.get("candidate_score_calibrated"),
            "price_at_signal": p.get("price_at_snapshot"),
            "price_observation_type": p.get("price_observation_type") or "OFFICIAL_CLOSE",
            "session_phase": origin_snap.get("session_phase") or p.get("session_phase"),
            "parent_signal_id": parent,
            "signal_family_id": signal_family_id(
                environment=env, ticker=ticker, explorer_run_id=xr, market_session_basis=session,
            ),
            "origin_snapshot_id": origin_snap.get("snapshot_id"),
            "legacy_backfill": True,
        }
        _, new = store.insert_canonical_signal(rec)
        if new:
            inserted += 1
        for m in members:
            mp = m.get("payload") or m
            obs = observation_record(
                identity={
                    "canonical_signal_id": cid, "explorer_run_id": xr,
                    "signal_family_id": rec["signal_family_id"], "parent_signal_id": parent,
                    "signal_origin": ident_origin, "market_state_fingerprint": fp,
                },
                analysis_type=m.get("analysis_type") or mp.get("analysis_type") or ANALYSIS_EXPLORER,
                ticker=ticker,
                environment=env,
                analysis_timestamp=m.get("analysis_timestamp_utc") or mp.get("analysis_timestamp_utc"),
                schedule_run_id=m.get("run_id") or mp.get("run_id"),
                generated_by="LEGACY_SNAPSHOT",
                extra={"origin_snapshot_id": m.get("snapshot_id"), "legacy_backfill": True, "import_status": "GENERATED"},
            )
            _, onew = store.insert_analysis_observation(obs)
            if onew:
                linked += 1
    return {"canonical_inserted": inserted, "observations_linked": linked, "legacy_snapshot_n": len(snaps)}
