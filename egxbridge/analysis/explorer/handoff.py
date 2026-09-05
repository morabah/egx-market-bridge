from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import shutil

from egxbridge import __version__ as BRIDGE_VERSION
from egxbridge.analysis import WORKFLOW_VERSION
from egxbridge.analysis.common.ai_mode import AI_CHATGPT_HANDOFF, assert_handoff_only
from egxbridge.analysis.common.environment import PRODUCTION, normalize_environment, workspace_root_for
from egxbridge.analysis.common.models import HandoffManifest, utc_now
from egxbridge.analysis.common.packaging import write_json, write_text, zip_directory, finalize_manifest
from egxbridge.analysis.common.provenance import bridge_market_evidence
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.explorer.models import ExplorerRunConfig
from egxbridge.analysis.explorer.candidate_context import build_candidate_row
from egxbridge.analysis.explorer.universe import build_explorer_universe
from egxbridge.analysis.explorer.coverage import classify_explorer_coverage
from egxbridge.analysis.explorer.intraday import enrich_shortlist_intraday
from egxbridge.analysis.explorer.prescreen import (
    normalize_scanner_metrics,
    score_candidates,
    candidate_reasons,
    candidate_warnings,
    classify_candidate_families,
    prescreen_score,
    enrich_metrics_fields,
)
from egxbridge.analysis.explorer.calibration import (
    calibration_config_from_run,
    ranking_comparison,
    correlation_profile,
    point_in_time_snapshot,
    lane_tops,
    diversify_by_lane,
    SCORE_KIND,
    SCORING_VERSION,
)
from egxbridge.analysis.explorer.intraday_select import (
    select_intraday_enrichment,
    lane_slots_from_run,
)
from egxbridge.storage import rows_to_csv
from egxbridge.universe import EQUITY


HERE = Path(__file__).resolve().parents[3]
EXPLORER_VERSION = "0.6.0"

CONTEXT_FILES = {
    "macro_holdings.md": """# A) Macro / Holdings — next session regime

Question:
What market/macro/portfolio regime matters for the **next working day**?

Use Bridge market evidence and any Funnel context as background only.

- Do not redefine Funnel Fair Value, Business Quality, Earnings Quality, or Financial Strength from short-term moves.
- Do not invent Level-2 / absorption / executed order-flow claims without depth/trades.
- If the official EGX calendar is not in this package, treat `target_next_working_day` as UNKNOWN and resolve the session date via web research.
- This file is regime context, not a stock-picking list.
- MOVE_ALREADY_REALIZED and FORWARD_SETUP_QUALITY are Explorer tactical fields; they do not change portfolio/macro conclusions by themselves.
""",
    "premarket_catalysts.md": """# B) Pre-Market Catalysts — what changed since last session

Question:
What changed since the last completed session that could affect **specific stocks**?

- Research news, disclosures, dividends, capital actions, and company-specific catalysts externally.
- Missing news in this Bridge package is expected — mark UNAVAILABLE when unknown; do not fabricate.
- A negative daily return does not disqualify a name (clean correction / retest setups exist).
- Verify catalysts outside the ZIP. Do not treat scanner scores as catalysts.
- For each candidate distinguish:
  1. MOVE_ALREADY_REALIZED — how much historical repricing is already in the price
  2. FORWARD_SETUP_QUALITY — whether a fresh next-session structure is present
  3. TECHNICAL_HISTORY_INTEGRITY — whether 3M/6M returns may be distorted
  4. candidate_lane — EARLY / CONTINUATION / CORRECTION / HIGH-RISK / FUNNEL
- Historical 3M/6M return alone is not a next-session catalyst.
- DELAYED_REPRICING_TECHNICAL_HYPOTHESIS requires an external catalyst check; the local bridge has no news feed.
""",
    "intraday_scanner.md": """# C) Intraday Scanner — confirmation for pre-screen candidates

Question:
Which **pre-screen candidates** require live/session confirmation?

- Use `intraday_enrichment.csv` (TradingView shortlist only). Missing intervals do not fail a candidate.
- Highest quantitative score ≠ best trade. `forward_setup_score` is HEURISTIC_UNCALIBRATED, not a probability.
- Inspect forward_setup_components, breakout/pre-breakout state, VOLATILITY_RISK, and confirmation needed.
- Do not infer order flow, absorption, or distribution from daily or incomplete intraday candles.
- Respect `execution_grade=NO` when depth/trades/bid-ask are absent.
- High RVOL is not automatically bullish — read `rvol_context` (direction, distance from high, volatility).
- Output WATCH / WAIT_FOR_CONFIRMATION / AVOID-style next-session notes — not BUY/SELL orders.
- The local bridge does not emit an exact Do-Not-Chase price. Use extension_context, ATR distance, and MOVE_ALREADY_REALIZED with news/psychology.
""",
    "value_quality_scan.md": """# D) Value & Quality Scan — Funnel follow-up

Question:
Which candidates deserve deeper investment / Full Funnel work?

- Use `funnel_context.csv` / `prior_funnel_context.json` as **context only**.
- Do not manufacture Fair Value. Do not change stored Funnel quality scores.
- MOVE_ALREADY_REALIZED = EXTREME does **not** downgrade Fair Value.
- A high Fair Value does **not** add a tactical Explorer score bonus.
- Keep economic valuation and realized-move context separate.
- PARTIAL Funnel → CONTINUE_FUNNEL (not delta-ready).
- NOT_FOUND + strong Explorer candidate → NEEDS_FULL_FUNNEL.
- CURRENT → NO_FUNNEL_ACTION unless you separately justify a delta with material new evidence.
- Intraday data must not redefine Fair Value / Business Quality / Sustainable Earnings / Earnings Quality / Financial Strength.
- Recommend FULL_FUNNEL or DELTA using `recommended_deep_analysis` plus your own catalyst check.
""",
    "weekly_xray.md": """# E) Weekly X-Ray — what worked, failed, or changed

Question:
What worked, failed, or changed across recent signals and Funnel states?

- Audit selection_basis, selection_bias_risk, and EXPLORER_COVERAGE.
- If coverage is INSUFFICIENT, do **not** present market-wide conclusions.
- Record whether the shortlist was BROAD_UNIVERSE or PARTIAL_UNIVERSE based on eligible coverage, not intent.
- Use `calibration_snapshots.jsonl` (point-in-time, no look-ahead). Outcomes are reserved nulls until a later session.
- Track whether high FORWARD_SETUP_QUALITY actually worked, and whether EXTREME MOVE_ALREADY_REALIZED reduced success.
- Compare `legacy_vs_calibrated_ranking.csv` to see whether 3M/6M still dominated ranking.
- Do not treat forward_setup_score as a validated hit-rate. Scores remain HEURISTIC_UNCALIBRATED until backtesting.
- This is a process audit, not a duplicate of the intraday scanner.
""",
}


def _funnel_registry_for(store, db, funnel_registry, environment: str):
    if funnel_registry is not None:
        return funnel_registry
    if store is None:
        return None
    from egxbridge.analysis.funnel.registry import FunnelRegistry
    env = normalize_environment(environment or getattr(store, "environment", PRODUCTION))
    return FunnelRegistry(
        store=store, db=db, environment=env,
        workspace_root=workspace_root_for(env),
    )


def _flatten_candidate(c: dict[str, Any]) -> dict[str, Any]:
    skip = {
        "funnel_context", "candidate_reasons", "candidate_families", "candidate_warnings",
        "intraday", "metrics", "candles", "funnel_ctx", "move_realized_reasons",
        "move_realized_detail", "forward_setup_components", "structure", "rvol_context",
        "history_integrity", "volatility_detail", "breakdown",
    }
    flat: dict[str, Any] = {}
    for k, v in c.items():
        if k in skip:
            continue
        if isinstance(v, dict):
            flat[k] = json.dumps(v, default=str)
        elif isinstance(v, list):
            if v and isinstance(v[0], dict):
                flat[k] = json.dumps(v, default=str)
            else:
                flat[k] = "|".join(str(x) for x in v)
        else:
            flat[k] = v
    flat["candidate_reasons"] = "|".join(str(x) for x in (c.get("candidate_reasons") or []))
    flat["candidate_families"] = "|".join(str(x) for x in (c.get("candidate_families") or []))
    flat["candidate_warnings"] = "|".join(str(x) for x in (c.get("candidate_warnings") or []))
    flat["move_realized_reasons"] = "|".join(str(x) for x in (c.get("move_realized_reasons") or []))
    for nk in (
        "forward_setup_components", "structure", "rvol_context", "history_integrity",
        "volatility_detail", "move_realized_detail", "breakdown",
    ):
        if c.get(nk) is not None and nk not in flat:
            flat[nk] = json.dumps(c.get(nk), default=str)
    for fk, fv in (c.get("funnel_context") or {}).items():
        flat[f"funnel_{fk}"] = fv
    intra = c.get("intraday") or {}
    if isinstance(intra, dict):
        flat["intraday_available"] = intra.get("intraday_available", c.get("intraday_available"))
    else:
        flat["intraday_available"] = c.get("intraday_available")
    struct = c.get("structure") or {}
    if isinstance(struct, dict):
        flat.setdefault("above_or_below_SMA20", struct.get("above_or_below_SMA20"))
        flat.setdefault("above_or_below_SMA50", struct.get("above_or_below_SMA50"))
    return flat


def prepare_explorer_handoff(
    config: ExplorerRunConfig | None = None,
    *,
    db=None,
    store: AnalysisStore | None = None,
    funnel_registry=None,
    output_root: Path | None = None,
    max_handoff_candidates: int | None = None,
    tradingview=None,
) -> dict[str, Any]:
    assert_handoff_only()
    config = config or ExplorerRunConfig()
    environment = normalize_environment(getattr(config, "environment", None) or getattr(store, "environment", None) or PRODUCTION)
    funnel_registry = _funnel_registry_for(store, db, funnel_registry, environment)

    uni = build_explorer_universe(
        db, explicit=config.universe or None, min_scanner_bars=getattr(config, "min_scanner_bars", 20),
    )
    tickers = list(uni.get("DISCOVERY_SYMBOLS") or uni.get("all_symbols") or uni.get("MAPPED_SYMBOLS") or [])
    config.universe = tickers

    generated_at = utc_now()
    date_tag = (config.target_date or generated_at[:10])
    dated = date_tag.replace("-", "")
    defaulted = output_root is None
    if output_root is None:
        out_root = HERE / "output" / "explorer_handoff" / date_tag
    else:
        out_root = Path(output_root)
    if out_root.exists():
        for p in out_root.iterdir():
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                shutil.rmtree(p)
    out_root.mkdir(parents=True, exist_ok=True)
    ctx_dir = out_root / "context"
    ctx_dir.mkdir(parents=True, exist_ok=True)

    records = {r.canonical_symbol: r for r in (uni.get("records") or [])}
    status_by = dict(uni.get("status_by_symbol") or {})
    watchlist = list(getattr(config, "watchlist", None) or [])

    universe_rows = []
    market_universe = []
    market_metrics = []
    scanner_rows = []
    unavailable_rows = []
    rejection_rows = []
    prior_funnel = []
    funnel_coverage = {
        "CURRENT": 0, "NEEDS_DELTA": 0, "STALE": 0, "NOT_FOUND": 0,
        "PARTIAL": 0, "REQUIRES_CONTINUATION": 0, "NOT_RELIABLE": 0,
    }
    latest_sessions: list[str] = []
    rdq_scores: list[float] = []
    exec_grades: list[str] = []

    for t in tickers:
        rec = records.get(t)
        st = status_by.get(t) or {}
        data_status = st.get("data_status") or uni.get("exclusion_reasons", {}).get(t, "DATA_UNAVAILABLE")
        reason = st.get("exclusion_reason") or uni.get("exclusion_reasons", {}).get(t, data_status)
        sec_type = st.get("security_type") or (rec.security_type if rec else None)

        if funnel_registry:
            fctx = funnel_registry.context_fields(t)
        else:
            fctx = {"ticker": t, "funnel_status": "NOT_FOUND", "Fair Value Range": None}
        status = fctx.get("funnel_status") or "NOT_FOUND"
        # Stock Explorer Funnel coverage is equities-only. Indices/funds are not NOT_FOUND stocks.
        if sec_type == EQUITY:
            funnel_coverage[status] = funnel_coverage.get(status, 0) + 1
            prior_funnel.append(fctx)

        universe_rows.append({
            "canonical_symbol": t,
            "display_name_if_known": getattr(rec, "display_name_if_known", "") if rec else "",
            "security_type": sec_type,
            "provider_alias_yahoo": getattr(rec, "provider_alias_yahoo", "") if rec else "",
            "provider_alias_tradingview": getattr(rec, "provider_alias_tradingview", "") if rec else "",
            "provider_alias_egid": getattr(rec, "provider_alias_egid", "") if rec else "",
            "is_tradable_candidate": getattr(rec, "is_tradable_candidate", False) if rec else False,
            "mapped": st.get("mapped"),
            "data_status": data_status,
            "exclusion_reason": reason,
            "daily_bars": st.get("daily_bars"),
            "latest_session": st.get("latest_session"),
            "source": getattr(rec, "source", "") if rec else uni.get("universe_source"),
        })

        eligible = t in (uni.get("SCANNER_ELIGIBLE_SYMBOLS") or [])
        if not eligible:
            row = {
                "ticker": t,
                "data_status": data_status,
                "research_data_quality": "UNKNOWN",
                "execution_grade": "NO",
                "available": False,
                "exclusion_reason": reason,
                "security_type": sec_type,
            }
            market_universe.append(row)
            unavailable_rows.append(row)
            market_metrics.append({
                "ticker": t, "available": False, "data_status": data_status,
                "exclusion_reason": reason,
            })
            rejection_rows.append({
                "ticker": t,
                "exclusion_reason": reason,
                "data_status": data_status,
                "security_type": sec_type,
                "stage": "UNIVERSE_OR_DATA_GATE",
            })
            continue

        evidence = bridge_market_evidence(db, t) if db is not None else {}
        metrics = enrich_metrics_fields(
            normalize_scanner_metrics(evidence.get("scanner_metrics") or {}),
            latest_session=evidence.get("latest_completed_market_session") or st.get("latest_session"),
        )
        sess = evidence.get("latest_completed_market_session") or evidence.get("session_date") or st.get("latest_session")
        if sess:
            latest_sessions.append(sess)
        if evidence.get("research_data_quality_score") is not None:
            try:
                rdq_scores.append(float(evidence["research_data_quality_score"]))
            except Exception:
                pass
        if evidence.get("execution_grade"):
            exec_grades.append(str(evidence.get("execution_grade")))

        market_universe.append({
            "ticker": t,
            "data_status": "DATA_AVAILABLE",
            "research_data_quality": evidence.get("research_data_quality"),
            "research_data_quality_score": evidence.get("research_data_quality_score"),
            "research_data_quality_grade": evidence.get("research_data_quality_grade"),
            "execution_data_quality": evidence.get("execution_data_quality"),
            "execution_data_quality_score": evidence.get("execution_data_quality_score"),
            "execution_data_quality_grade": evidence.get("execution_data_quality_grade"),
            "execution_grade": evidence.get("execution_grade"),
            "session_date": sess,
            "latest_completed_market_session": sess,
            "missing_capabilities": ",".join(evidence.get("missing_capabilities") or []),
            "providers_used": ",".join(evidence.get("providers_used") or []),
            "intraday_available": "intraday_ohlcv" not in (evidence.get("missing_capabilities") or []),
            "security_type": sec_type,
            "exclusion_reason": reason,
        })
        market_metrics.append({
            "ticker": t,
            **metrics,
            "data_status": "DATA_AVAILABLE",
            "timing_uses_normalized_only": True,
        })
        scanner_rows.append({
            "ticker": t,
            "metrics": metrics,
            "funnel_ctx": fctx,
            "market_source_evidence": {k: evidence.get(k) for k in (
                "providers_used", "research_data_quality_score", "research_data_quality_grade",
                "execution_data_quality_score", "execution_grade", "missing_capabilities",
                "freshness_class", "price_integrity", "capture_timestamp")},
            "candles": evidence.get("daily_candles_timing_safe") or evidence.get("daily_candles") or [],
            "prescreen_score": prescreen_score(metrics),
            "candidate_reasons": candidate_reasons(metrics),
            "candidate_families": classify_candidate_families(metrics, watchlist=t in {w.upper() for w in watchlist}),
            "candidate_warnings": candidate_warnings(metrics),
        })

    equity_n = int(uni.get("EQUITY_UNIVERSE_TOTAL") or 0)
    yahoo_mapped_eq = [
        s for s, st in status_by.items()
        if st.get("mapped") and st.get("security_type") == EQUITY
    ]
    coverage = classify_explorer_coverage(
        equity_universe_total=equity_n,
        mapped_symbols=len(yahoo_mapped_eq),
        daily_data_available=len(uni.get("DAILY_DATA_AVAILABLE") or []),
        scanner_eligible=len(uni.get("SCANNER_ELIGIBLE_SYMBOLS") or []),
        thresholds={
            "HIGH": getattr(config, "coverage_high", 80.0),
            "MEDIUM": getattr(config, "coverage_medium", 60.0),
            "LOW": getattr(config, "coverage_low", 30.0),
        },
    )
    selection_basis = coverage["selection_basis"]
    selection_bias_risk = coverage["selection_bias_risk"]
    config.selection_basis = selection_basis
    config.selection_bias_risk = selection_bias_risk

    prescreen_limit = int(getattr(config, "prescreen_limit", 30) or 30)
    intraday_limit = int(getattr(config, "intraday_limit", 15) or 15)
    handoff_limit = int(max_handoff_candidates or getattr(config, "handoff_limit", 20) or 20)
    cal_cfg = calibration_config_from_run(config)

    all_scored = score_candidates(scanner_rows, watchlist=watchlist, cfg=cal_cfg)
    ranked_cmp = ranking_comparison(all_scored)
    ranked_by_ticker = {r["ticker"]: r for r in ranked_cmp}
    corr_legacy = correlation_profile(all_scored, "candidate_score_legacy")
    corr_calibrated = correlation_profile(all_scored, "candidate_score_calibrated")
    lane_leaders = lane_tops(all_scored, n=5)

    prescreen_all = diversify_by_lane(all_scored, max_handoff=prescreen_limit, cfg=cal_cfg)
    selected_tickers = {c["ticker"] for c in prescreen_all}
    for row in all_scored:
        if row["ticker"] not in selected_tickers:
            rejection_rows.append({
                "ticker": row["ticker"],
                "exclusion_reason": "NOT_IN_PRESCREEN_SHORTLIST",
                "data_status": "SCANNER_ELIGIBLE",
                "candidate_score": row.get("candidate_score_calibrated"),
                "candidate_score_legacy": row.get("candidate_score_legacy"),
                "candidate_families": "|".join(row.get("candidate_families") or []),
                "candidate_lane": row.get("candidate_lane"),
                "stage": "PRESCREEN",
            })

    enrich_sel = select_intraday_enrichment(
        prescreen_all, intraday_limit, lane_slots=lane_slots_from_run(config),
    )
    enrich_tickers = [s["ticker"] for s in enrich_sel]
    enrich_meta = {s["ticker"]: s for s in enrich_sel}
    intraday_pack = {"queried_tickers": [], "rows": [], "failures": [], "by_ticker": {}, "intraday_enriched": 0}
    if getattr(config, "enrich_intraday", True) and enrich_tickers:
        tv = tradingview
        if tv is None:
            try:
                from egxbridge.config import Settings
                from egxbridge.symbols import SymbolRegistry
                from egxbridge.providers.tradingview import TradingViewProvider
                settings = Settings.load(HERE / "config.json")
                registry = SymbolRegistry.from_config({"symbol_aliases": settings.symbol_aliases})
                tv = TradingViewProvider(
                    registry,
                    enabled=bool((settings.enabled_providers or {}).get("tradingview", True)),
                    username=settings.tradingview_username,
                    password=settings.tradingview_password,
                )
            except Exception:
                tv = None
        intraday_pack = enrich_shortlist_intraday(enrich_tickers, tv=tv)

    handoff_shortlist = prescreen_all[:handoff_limit]
    candidate_metrics = []
    for item in handoff_shortlist:
        t = item["ticker"]
        fctx = item["funnel_ctx"]
        metrics = item["metrics"]
        struct = item.get("structure") or {}
        rank_row = ranked_by_ticker.get(t) or {}
        extra = {
            "candidate_score_legacy": item.get("candidate_score_legacy"),
            "candidate_score_calibrated": item.get("candidate_score_calibrated"),
            "prescreen_score": item.get("prescreen_score"),
            "MOVE_ALREADY_REALIZED": item.get("MOVE_ALREADY_REALIZED"),
            "move_realized_reasons": item.get("move_realized_reasons") or [],
            "FORWARD_SETUP_QUALITY": item.get("FORWARD_SETUP_QUALITY"),
            "forward_setup_score": item.get("forward_setup_score"),
            "forward_setup_components": item.get("forward_setup_components"),
            "candidate_lane": item.get("candidate_lane"),
            "TECHNICAL_HISTORY_INTEGRITY": item.get("TECHNICAL_HISTORY_INTEGRITY"),
            "VOLATILITY_RISK": item.get("VOLATILITY_RISK"),
            "structure": struct,
            "rvol_context": item.get("rvol_context"),
            "history_integrity": item.get("history_integrity"),
            "volatility_detail": item.get("volatility_detail"),
            "breakdown": item.get("breakdown"),
            "score_kind": item.get("score_kind") or SCORE_KIND,
            "not_a_probability": True,
            "fair_value_used_in_tactical_score": False,
            "do_not_chase_price": item.get("do_not_chase_price"),
            "do_not_chase_note": item.get("do_not_chase_note"),
            "extension_context": item.get("extension_context"),
            "legacy_rank": rank_row.get("legacy_rank"),
            "calibrated_rank": rank_row.get("calibrated_rank"),
            "rank_change": rank_row.get("rank_change"),
            "reason_for_change": rank_row.get("reason_for_change"),
            "above_or_below_SMA20": struct.get("above_or_below_SMA20"),
            "above_or_below_SMA50": struct.get("above_or_below_SMA50"),
            "breakout_reference": struct.get("breakout_reference"),
            "distance_to_breakout_pct": struct.get("distance_to_breakout_pct"),
            "prebreakout_volume_state": struct.get("prebreakout_volume_state"),
            "extension_state": struct.get("extension_state"),
            "recent_peak": struct.get("recent_peak"),
            "drawdown_from_recent_peak_pct": struct.get("drawdown_from_recent_peak_pct"),
            "drawdown_in_ATR": struct.get("drawdown_in_ATR"),
            "scoring_version": SCORING_VERSION,
            "intraday_selection_reason": (enrich_meta.get(t) or {}).get("intraday_selection_reason"),
            "intraday_selection_lane": (enrich_meta.get(t) or {}).get("intraday_selection_lane"),
            "intraday_selection_rank_within_lane": (enrich_meta.get(t) or {}).get("intraday_selection_rank_within_lane"),
        }
        row = build_candidate_row(
            t, metrics, fctx,
            selection_basis=selection_basis,
            selection_bias_risk=selection_bias_risk,
            candidate_reasons=item.get("candidate_reasons"),
            candidate_families=item.get("candidate_families"),
            candidate_warnings=item.get("candidate_warnings"),
            data_status="SCANNER_ELIGIBLE",
            candidate_score=item.get("candidate_score_calibrated") or item.get("candidate_score"),
            extra=extra,
        )
        row["prescreen_score"] = item.get("prescreen_score")
        row["intraday"] = (intraday_pack.get("by_ticker") or {}).get(t) or {
            "ticker": t, "intraday_available": False, "intervals": [],
        }
        row["intraday_available"] = bool(row["intraday"].get("intraday_available"))
        if fctx.get("funnel_status") == "NOT_FOUND":
            row["fair_value_from_funnel_only"] = None
            row["funnel_context"]["Fair Value Range"] = None
            row["fair_value_manufactured"] = False
        candidate_metrics.append(row)

    # --- files (v0.5 names + backward-compatible aliases) ---
    rows_to_csv(out_root / "universe.csv", universe_rows)
    rows_to_csv(out_root / "market_universe.csv", market_universe)
    rows_to_csv(out_root / "universe_failures.csv", unavailable_rows or [{"note": "none"}])
    rows_to_csv(out_root / "data_unavailable.csv", unavailable_rows or [{"note": "none"}])
    rows_to_csv(out_root / "daily_market_metrics.csv", market_metrics)
    rows_to_csv(out_root / "market_metrics.csv", market_metrics)
    from egxbridge.analysis.schedule.market_summary import (
        compute_breadth, compact_scanner_metric_row, market_participation,
        MARKET_BREADTH_SCOPE, SHORTLIST_BREADTH_LABEL,
    )
    eligible_syms = {str(s).upper() for s in (uni.get("SCANNER_ELIGIBLE_SYMBOLS") or [])}
    scanner_eligible_metrics = []
    for row in market_metrics:
        t = str(row.get("ticker") or "").upper()
        if t not in eligible_syms:
            continue
        rec = dict(row)
        rec["security_type"] = EQUITY
        scanner_eligible_metrics.append(compact_scanner_metric_row(rec))
    market_breadth = compute_breadth(
        scanner_eligible_metrics, scope=MARKET_BREADTH_SCOPE, label="BROAD_MARKET_EVIDENCE",
    )
    candidate_breadth = compute_breadth(
        [compact_scanner_metric_row(c) for c in candidate_metrics],
        scope=SHORTLIST_BREADTH_LABEL, label=SHORTLIST_BREADTH_LABEL,
    )
    write_json(out_root / "market_breadth.json", {
        "MARKET_BREADTH_SCOPE": MARKET_BREADTH_SCOPE,
        "market_breadth": market_breadth,
        "market_participation": market_participation(market_breadth),
        "candidate_breadth": candidate_breadth,
        "scoring_version": SCORING_VERSION,
        "note": "Market breadth uses SCANNER_ELIGIBLE_EQUITY_UNIVERSE. Candidate breadth is not market breadth.",
    })
    rows_to_csv(out_root / "prescreen_candidates.csv", [_flatten_candidate({
        **c,
        "ticker": c["ticker"],
        "candidate_score": c.get("candidate_score_calibrated") or c.get("candidate_score"),
        "candidate_score_calibrated": c.get("candidate_score_calibrated"),
        "candidate_score_legacy": c.get("candidate_score_legacy") or c.get("prescreen_score"),
        "candidate_families": c.get("candidate_families"),
        "candidate_reasons": c.get("candidate_reasons"),
        "candidate_warnings": c.get("candidate_warnings"),
        "funnel_status": (c.get("funnel_ctx") or {}).get("funnel_status"),
        "funnel_context": (c.get("funnel_ctx") or {}),
        "intraday_available": bool(((intraday_pack.get("by_ticker") or {}).get(c["ticker"]) or {}).get("intraday_available")),
    }) for c in prescreen_all] or [{"note": "none"}])
    rows_to_csv(out_root / "prescreen_candidates_calibrated.csv", [_flatten_candidate({
        **c,
        "funnel_status": (c.get("funnel_ctx") or {}).get("funnel_status"),
        "funnel_context": (c.get("funnel_ctx") or {}),
        "intraday_available": bool(((intraday_pack.get("by_ticker") or {}).get(c["ticker"]) or {}).get("intraday_available")),
        **(ranked_by_ticker.get(c["ticker"]) or {}),
        "ticker": c["ticker"],
        "candidate_families": c.get("candidate_families"),
        "candidate_reasons": c.get("candidate_reasons"),
        "candidate_warnings": c.get("candidate_warnings"),
        "MOVE_ALREADY_REALIZED": c.get("MOVE_ALREADY_REALIZED"),
        "FORWARD_SETUP_QUALITY": c.get("FORWARD_SETUP_QUALITY"),
        "forward_setup_score": c.get("forward_setup_score"),
        "forward_setup_components": c.get("forward_setup_components"),
        "TECHNICAL_HISTORY_INTEGRITY": c.get("TECHNICAL_HISTORY_INTEGRITY"),
        "VOLATILITY_RISK": c.get("VOLATILITY_RISK"),
        "candidate_lane": c.get("candidate_lane"),
        "structure": c.get("structure"),
        "rvol_context": c.get("rvol_context"),
        "metrics": c.get("metrics"),
        "daily_return": (c.get("metrics") or {}).get("daily_return_pct"),
        "return_1w": (c.get("metrics") or {}).get("return_1w_pct"),
        "return_1m": (c.get("metrics") or {}).get("return_1m_pct"),
        "return_3m": (c.get("metrics") or {}).get("return_3m_pct"),
        "return_6m": (c.get("metrics") or {}).get("return_6m_pct"),
        "RVOL20": (c.get("metrics") or {}).get("rvol_20"),
        "distance_20d_high": (c.get("metrics") or {}).get("dist_from_20d_high_pct"),
        "distance_60d_high": (c.get("metrics") or {}).get("dist_from_60d_high_pct"),
        "breakout_20d": c.get("breakout_20d"),
        "breakout_60d": c.get("breakout_60d"),
        "intraday_available": bool(((intraday_pack.get("by_ticker") or {}).get(c["ticker"]) or {}).get("intraday_available")),
        "score_kind": SCORE_KIND,
        "not_a_probability": True,
    }) for c in prescreen_all] or [{"note": "none"}])
    rows_to_csv(out_root / "legacy_vs_calibrated_ranking.csv", ranked_cmp or [{"note": "none"}])
    hist_rows = []
    for c in all_scored:
        hi = c.get("history_integrity") or {}
        det = (hi.get("detector") or {}) if isinstance(hi, dict) else {}
        hist_rows.append({
            "ticker": c.get("ticker"),
            "TECHNICAL_HISTORY_INTEGRITY": c.get("TECHNICAL_HISTORY_INTEGRITY"),
            "long_horizon_weight": hi.get("long_horizon_weight") if isinstance(hi, dict) else None,
            "reasons": "|".join(hi.get("reasons") or []) if isinstance(hi, dict) else "",
            "possible_discontinuity": det.get("possible_discontinuity"),
            "max_one_session_abs_return": det.get("max_one_session_abs_return"),
            "clues": "|".join(det.get("clues") or []),
            "return_3m": (c.get("metrics") or {}).get("return_3m_pct"),
            "return_6m": (c.get("metrics") or {}).get("return_6m_pct"),
        })
    rows_to_csv(out_root / "history_integrity_flags.csv", hist_rows or [{"note": "none"}])
    rows_to_csv(out_root / "prescreen_rejections.csv", rejection_rows or [{"note": "none"}])
    rows_to_csv(out_root / "intraday_enrichment.csv", intraday_pack.get("rows") or [{"note": "none"}])
    rows_to_csv(out_root / "intraday_failures.csv", intraday_pack.get("failures") or [{"note": "none"}])

    cand_flat = [_flatten_candidate(c) for c in candidate_metrics]
    rows_to_csv(out_root / "candidate_metrics.csv", cand_flat or [{"note": "none"}])

    funnel_ctx_rows = []
    for f in prior_funnel:
        funnel_ctx_rows.append({
            "ticker": f.get("ticker"),
            "funnel_status": f.get("funnel_status"),
            "funnel_completion_status": f.get("funnel_completion_status"),
            "delta_eligible": f.get("delta_eligible"),
            "valuation_status": f.get("valuation_status"),
            "Valuation Date": f.get("Valuation Date"),
            "Business Quality": f.get("Business Quality"),
            "Earnings Quality": f.get("Earnings Quality"),
            "Financial Strength": f.get("Financial Strength"),
            "Growth": f.get("Growth"),
            "Economic Valuation": f.get("Economic Valuation"),
            "Fair Value Range": f.get("Fair Value Range"),
            "Integrated Risk": f.get("Integrated Risk"),
            "Final Decision Domain": f.get("Final Decision Domain"),
            "environment": environment,
        })
    rows_to_csv(out_root / "funnel_context.csv", funnel_ctx_rows or [{"note": "none"}])

    provider_quality = []
    provider_health = []
    if db is not None:
        try:
            provider_health = db.fetch_provider_status()
            provider_quality = provider_health
        except Exception:
            pass
    rows_to_csv(out_root / "provider_quality.csv", provider_quality or [{"note": "unavailable"}])
    rows_to_csv(out_root / "provider_health.csv", provider_health or [{"note": "unavailable"}])

    counts = {
        "UNIVERSE_TOTAL": uni["UNIVERSE_TOTAL"],
        "EQUITY_UNIVERSE_TOTAL": uni.get("EQUITY_UNIVERSE_TOTAL"),
        "MAPPED_SYMBOLS": len(yahoo_mapped_eq),
        "UNMAPPED_SYMBOLS": len(uni.get("UNMAPPED_SYMBOLS") or []),
        "DAILY_DATA_AVAILABLE": len(uni.get("DAILY_DATA_AVAILABLE") or []),
        "DAILY_DATA_UNAVAILABLE": len(uni.get("DAILY_DATA_UNAVAILABLE") or []),
        "DAILY_DATA_STALE_EXPECTED": len(uni.get("DAILY_DATA_STALE_EXPECTED") or []),
        "DAILY_DATA_STALE_UNEXPECTED": len(uni.get("DAILY_DATA_STALE_UNEXPECTED") or []),
        "SCANNER_ELIGIBLE_SYMBOLS": len(uni.get("SCANNER_ELIGIBLE_SYMBOLS") or []),
        "PRESCREEN_SELECTED": len(prescreen_all),
        "INTRADAY_ENRICHED": int(intraday_pack.get("intraday_enriched") or 0),
        "HANDOFF_CANDIDATES": len(candidate_metrics),
        "universe_total": uni["UNIVERSE_TOTAL"],
        "mapped_symbols": len(yahoo_mapped_eq),
        "data_eligible_count": len(uni.get("DAILY_DATA_AVAILABLE") or []),
        "data_unavailable_count": len(uni.get("DAILY_DATA_UNAVAILABLE") or []),
        "scanner_candidate_count": len(scanner_rows),
        "handoff_candidate_count": len(candidate_metrics),
        "DATA_AVAILABLE_SYMBOLS": uni.get("DAILY_DATA_AVAILABLE") or [],
        "DATA_UNAVAILABLE_SYMBOLS": uni.get("DAILY_DATA_UNAVAILABLE") or [],
        "SCANNER_ELIGIBLE_SYMBOLS_LIST": uni.get("SCANNER_ELIGIBLE_SYMBOLS") or [],
        "MAPPED_SYMBOLS_COUNT": len(yahoo_mapped_eq),
        "universe_source": uni.get("universe_source"),
        "security_type_counts": uni.get("security_type_counts") or {},
        "exclusion_summary": {
            "DATA_UNAVAILABLE": len(uni.get("DAILY_DATA_UNAVAILABLE") or []),
            "not_in_handoff_shortlist": max(0, len(scanner_rows) - len(candidate_metrics)),
        },
        "funnel_coverage_scope": "EQUITY_UNIVERSE_TOTAL",
        "funnel_coverage_denominator": equity_n,
        "funnel_coverage_n": sum(int(v or 0) for v in funnel_coverage.values()),
        "funnel_status_counts": dict(funnel_coverage),
        **{k: coverage[k] for k in (
            "mapped_coverage_pct", "daily_data_coverage_pct", "scanner_eligible_coverage_pct",
            "eligible_coverage_pct", "EXPLORER_COVERAGE", "selection_basis", "selection_bias_risk",
            "market_wide_confidence_allowed",
        )},
    }
    latest_session = max(latest_sessions) if latest_sessions else None
    from egxbridge.analysis.schedule.identity import make_explorer_run_id
    explorer_run_id = make_explorer_run_id(
        environment=environment, latest_session=latest_session, generated_at=generated_at,
    )
    universe_summary = {
        "bridge_version": BRIDGE_VERSION,
        "explorer_version": EXPLORER_VERSION,
        "generated_at": generated_at,
        "environment": environment,
        "counts": counts,
        "security_type_counts": uni.get("security_type_counts") or {},
        "coverage": coverage,
        "universe_source": uni.get("universe_source"),
        "sources": uni.get("sources") or [],
    }
    write_json(out_root / "universe_summary.json", universe_summary)
    write_json(out_root / "universe_coverage.json", counts)
    write_json(out_root / "prescreen_stage_a.json", {
        "stage": "A",
        "description": "Deterministic broad-universe pre-screen; production rank is candidate_score_calibrated (HEURISTIC_UNCALIBRATED)",
        "no_buy_recommendations": True,
        "score_kind": SCORE_KIND,
        "not_a_probability": True,
        "shortlist_size": len(prescreen_all),
        "selection_basis": selection_basis,
        "selection_bias_risk": selection_bias_risk,
        "lane_tops": lane_leaders,
        "intraday_queried_tickers": enrich_tickers,
        "candidates": [
            {
                "ticker": c["ticker"],
                "candidate_score": c.get("candidate_score_calibrated"),
                "candidate_score_calibrated": c.get("candidate_score_calibrated"),
                "candidate_score_legacy": c.get("candidate_score_legacy"),
                "candidate_lane": c.get("candidate_lane"),
                "candidate_families": c.get("candidate_families"),
                "candidate_reasons": c.get("candidate_reasons"),
                "candidate_warnings": c.get("candidate_warnings"),
                "MOVE_ALREADY_REALIZED": c.get("MOVE_ALREADY_REALIZED"),
                "FORWARD_SETUP_QUALITY": c.get("FORWARD_SETUP_QUALITY"),
                "forward_setup_score": c.get("forward_setup_score"),
                "TECHNICAL_HISTORY_INTEGRITY": c.get("TECHNICAL_HISTORY_INTEGRITY"),
                "VOLATILITY_RISK": c.get("VOLATILITY_RISK"),
                "breakout_20d": c.get("breakout_20d"),
                "breakout_60d": c.get("breakout_60d"),
                "score_kind": SCORE_KIND,
                "not_a_probability": True,
            }
            for c in prescreen_all
        ],
    })
    write_json(out_root / "prior_funnel_context.json", prior_funnel)
    write_json(out_root / "funnel_coverage.json", funnel_coverage)
    write_json(out_root / "funnel_coverage_meta.json", {
        "scope": "EQUITY_UNIVERSE_TOTAL",
        "denominator": equity_n,
        "n": sum(int(v or 0) for v in funnel_coverage.values()),
        "counts": funnel_coverage,
        "indices_and_funds_excluded_from_funnel_not_found": True,
        "note": "Stock Explorer Funnel coverage is over equities only; indices/funds are not Funnel NOT_FOUND stocks.",
    })
    write_json(out_root / "intraday_selection.json", {
        "limit": intraday_limit,
        "lane_slots": lane_slots_from_run(config),
        "selected": enrich_sel,
        "note": "Selection does not change candidate_score_calibrated",
        "scoring_version": SCORING_VERSION,
    })

    for name, text in CONTEXT_FILES.items():
        write_text(ctx_dir / name, text)

    rdq_summary = {
        "count": len(rdq_scores),
        "mean": round(sum(rdq_scores) / len(rdq_scores), 2) if rdq_scores else None,
        "min": min(rdq_scores) if rdq_scores else None,
        "max": max(rdq_scores) if rdq_scores else None,
    }
    exec_summary = {
        "grades": sorted({g for g in exec_grades}),
        "execution_grade_typically": "NO",
        "note": "Bid/ask/depth/trades are not required for daily pre-screen eligibility",
    }

    payload = {
        "generated_at": generated_at,
        "horizon": config.horizon,
        "target_date": config.target_date,
        "target_next_working_day": "UNKNOWN",
        "target_session_status": "UNKNOWN",
        "latest_completed_market_session": latest_session,
        "package_generated_at": generated_at,
        "ai_mode": AI_CHATGPT_HANDOFF,
        "environment": environment,
        "stage_a": "deterministic_prescreen",
        "stage_b": "chatgpt_handoff",
        "universe_total": counts["universe_total"],
        "equity_universe_total": counts["EQUITY_UNIVERSE_TOTAL"],
        "data_eligible_count": counts["data_eligible_count"],
        "scanner_candidate_count": counts["scanner_candidate_count"],
        "handoff_candidate_count": counts["handoff_candidate_count"],
        "counts": counts,
        "coverage": coverage,
        "funnel_coverage": funnel_coverage,
        "funnel_status_counts": funnel_coverage,
        "selection_basis": selection_basis,
        "selection_bias_risk": selection_bias_risk,
        "rules": [
            "This is Explorer/tactical analysis, not Full Funnel valuation.",
            "The local pre-screen is NOT a recommendation.",
            "Distinguish for each candidate: (A) how much of the historical move is already realized, (B) whether a fresh forward setup exists, (C) whether an official/company/news catalyst exists, (D) whether Funnel/valuation support is available, (E) whether the stock is too extended to chase, (F) what confirmation is required next session, (G) INVESTMENT / HYBRID / SPECULATION / WATCH ONLY / AVOID.",
            "Do not let historical 3M/6M return alone drive next-session recommendations.",
            "candidate_score_calibrated is the production Explorer rank. candidate_score_legacy is diagnostic only.",
            "forward_setup_score is HEURISTIC_UNCALIBRATED — not a probability of profit.",
            "Do not assume the highest quantitative score is the best trade.",
            "Incorporate news, disclosures, macro, market regime, psychology, company-specific catalysts, and existing Funnel context.",
            "Verify catalysts externally. DELAYED_REPRICING_TECHNICAL_HYPOTHESIS requires that check.",
            "Respect missing execution data. Do not infer order flow, accumulation, distribution, or absorption when trades/depth are absent.",
            "Produce next-working-day WATCH/WAIT/AVOID-style conclusions. The local bridge does not generate BUY/SELL orders.",
            "Do not modify stored Funnel Fair Value, Business Quality, Earnings Quality, or Financial Strength.",
            "A high Fair Value is not a tactical-score bonus. EXTREME MOVE_ALREADY_REALIZED does not change Fair Value.",
            "DATA_UNAVAILABLE and excluded tickers are listed, not silently dropped.",
            "If EXPLORER_COVERAGE is INSUFFICIENT, do not present market-wide conclusions.",
            "target_next_working_day is UNKNOWN unless an official EGX calendar is available locally — do not guess holidays.",
            "No exact Do-Not-Chase price is generated without an execution rule; use extension/ATR/move-realized with news.",
        ],
        "candidates": candidate_metrics,
        "scanner_eligible_metrics": scanner_eligible_metrics,
        "market_breadth": market_breadth,
        "market_participation": market_participation(market_breadth),
        "candidate_breadth": candidate_breadth,
        "intraday_queried_tickers": intraday_pack.get("queried_tickers") or [],
        "lane_tops": lane_leaders,
        "score_kind": SCORE_KIND,
        "scoring_version": SCORING_VERSION,
        "explorer_run_id": explorer_run_id,
        "not_a_probability": True,
        "correlation_legacy": corr_legacy,
        "correlation_calibrated": corr_calibrated,
        "intraday_selection": enrich_sel,
        "orders_generated": False,
    }
    write_json(out_root / "explorer_handoff.json", payload)
    write_text(out_root / "explorer_handoff.md", f"""# EGX Explorer Handoff — {config.horizon}

Generated: {payload['generated_at']}
AI MODE: CHATGPT_HANDOFF
Explorer version: {EXPLORER_VERSION}
Analysis environment: {environment}
Score kind: {SCORE_KIND} (not a probability)

## Purpose

This is **Explorer / tactical analysis**, not Full Funnel valuation.
The local bridge does **not** generate BUY/SELL orders.
The local pre-screen is **not** a recommendation.

## Coverage

- UNIVERSE_TOTAL: {counts['UNIVERSE_TOTAL']}
- EQUITY_UNIVERSE_TOTAL: {counts['EQUITY_UNIVERSE_TOTAL']}
- MAPPED_SYMBOLS: {counts['MAPPED_SYMBOLS']}
- UNMAPPED_SYMBOLS: {counts['UNMAPPED_SYMBOLS']}
- DAILY_DATA_AVAILABLE: {counts['DAILY_DATA_AVAILABLE']}
- DAILY_DATA_UNAVAILABLE: {counts['DAILY_DATA_UNAVAILABLE']}
- SCANNER_ELIGIBLE_SYMBOLS: {counts['SCANNER_ELIGIBLE_SYMBOLS']}
- PRESCREEN_SELECTED: {counts['PRESCREEN_SELECTED']}
- INTRADAY_ENRICHED: {counts['INTRADAY_ENRICHED']}
- HANDOFF_CANDIDATES: {counts['HANDOFF_CANDIDATES']}
- daily_data_coverage_pct: {counts['daily_data_coverage_pct']}
- scanner_eligible_coverage_pct: {counts['scanner_eligible_coverage_pct']}
- EXPLORER_COVERAGE: {counts['EXPLORER_COVERAGE']}
- selection_basis: {selection_basis}
- selection_bias_risk: {selection_bias_risk}

Funnel status counts (production environment only): see funnel_coverage.json (structured object, not a string).

latest_completed_market_session: {latest_session or 'UNKNOWN'}
package_generated_at: {generated_at}
target_next_working_day: UNKNOWN
target_session_status: UNKNOWN

{"**Coverage is INSUFFICIENT — do not present market-wide conclusions.**" if not coverage.get("market_wide_confidence_allowed") else ""}

## Two dimensions (keep them separate)

For every candidate, answer:

- **A. MOVE_ALREADY_REALIZED** — how much of the historical move is already in the price? (LOW / MODERATE / HIGH / EXTREME / NOT_RELIABLE). This is not a sell signal.
- **B. FORWARD_SETUP_QUALITY** — is there a fresh next-session structure? (STRONG / GOOD / MIXED / WEAK / NOT_RELIABLE). `forward_setup_score` is heuristic, not P(profit).
- **C.** Is there an official/company/news catalyst? Verify externally.
- **D.** Is Funnel / valuation support available? Context only — do not change Fair Value.
- **E.** Is the stock too extended to chase? Use MOVE_ALREADY_REALIZED, ATR distance, extension_context. No exact Do-Not-Chase price is provided.
- **F.** What confirmation is required next session?
- **G.** Classify the opportunity as INVESTMENT / HYBRID / SPECULATION / WATCH ONLY / AVOID.

Do **not** let 3M/6M historical return alone drive next-session recommendations.

Production rank = `candidate_score_calibrated`. `candidate_score_legacy` is diagnostic comparison only.

## ChatGPT instructions

- Do not assume the highest quantitative score is the best trade.
- Incorporate news, disclosures, macro, market regime, psychology, company-specific catalysts, and existing Funnel context.
- Verify catalysts externally. DELAYED_REPRICING_TECHNICAL_HYPOTHESIS is a local technical pattern only.
- Respect missing execution data. Do not infer order flow, accumulation, distribution, or absorption when trades/depth are absent.
- Produce next-working-day actionable WATCH / WAIT / AVOID-style conclusions.
- Stage A already produced a transparent quantitative shortlist (`prescreen_stage_a.json`) diversified across candidate lanes.
- Use `context/*.md` as five **distinct** schedule lenses.
- Use CSVs as quantitative evidence with provenance.
- Use `prior_funnel_context.json` as context only — never manufacture Fair Value.
- High Fair Value is not a tactical bonus. EXTREME realized move does not rewrite Fair Value.

Do **not** place orders. Do **not** change Fair Value. Do **not** treat scores as probabilities.
""")
    write_text(out_root / "README.md", """# EGX Explorer ChatGPT Handoff (v0.6)

Upload this ZIP to ChatGPT. No paid API key is used by EGX Market Bridge.

scoring_version is frozen at 0.5.1. v0.6 adds 5-schedule packages and point-in-time snapshots.

See python -m egxbridge.analysis.prepare_schedules for the five independent analysis jobs.
""")

    snap_path = out_root / "calibration_snapshots.jsonl"
    from egxbridge.analysis.schedule.session import session_context as _session_context
    from egxbridge.analysis.schedule.snapshots import build_signal_snapshot, persist_snapshots
    from egxbridge.analysis.schedule.types import ANALYSIS_EXPLORER
    sess_meta = _session_context()
    explorer_run_key = explorer_run_id
    pit_snaps = []
    with snap_path.open("w", encoding="utf-8") as fh:
        for c in prescreen_all:
            legacy_pit = point_in_time_snapshot(c, generated_at=generated_at, session=latest_session)
            legacy_pit["scoring_version"] = SCORING_VERSION
            fh.write(json.dumps(legacy_pit, default=str) + "\n")
        for c in candidate_metrics:
            pit_snaps.append(build_signal_snapshot(
                c, run_id=explorer_run_key, environment=environment,
                analysis_type=ANALYSIS_EXPLORER, generated_at=generated_at,
                latest_session=latest_session, session_meta=sess_meta,
                explorer_run_id=explorer_run_id,
            ))
    snap_stats = {"inserted": 0, "ignored_duplicates": 0, "snapshot_ids": []}
    if store:
        snap_stats = persist_snapshots(store, pit_snaps)
        from egxbridge.analysis.forward_validation import freeze_explorer_run
        scored_by_ticker = {c["ticker"]: c for c in all_scored}
        forward = freeze_explorer_run(
            store, run_id=explorer_run_id, generated_at=generated_at, market_session=latest_session,
            all_candidates=[{**r, **scored_by_ticker.get(r["ticker"], {}), "candles": r.get("candles") or [],
                "calibrated_rank": (ranked_by_ticker.get(r["ticker"]) or {}).get("calibrated_rank"),
                "exclusion_reason": None if r["ticker"] in scored_by_ticker else "DATA_UNAVAILABLE"} for r in scanner_rows],
            prescreen_tickers=selected_tickers, final_tickers={c["ticker"] for c in candidate_metrics},
            intraday_tickers=set(enrich_tickers), market_breadth=market_breadth, selection_basis=selection_basis,
            benchmark=db.fetch_candles("EGX30", "1d", limit=400) if db else [],
        )
        payload["forward_validation_snapshot"] = forward
        write_json(out_root / "explorer_handoff.json", payload)
    write_json(out_root / "signal_calibration_diagnostics.json", {
        "score_kind": SCORE_KIND,
        "not_a_probability": True,
        "transform": {
            "saturating": "ln(1+|r|/scale)",
            "scales": {"1d": 4, "1w": 8, "1m": 15, "3m": 25, "6m": 40},
            "long_horizon_cap": 4.0,
            "not_verified_weight": 0.35,
            "possible_discontinuity_long_horizon_weight": 0.0,
        },
        "correlation_legacy": corr_legacy,
        "correlation_calibrated": corr_calibrated,
        "lane_tops": lane_leaders,
        "intraday_queried_tickers": enrich_tickers,
        "eligible_scored": len(all_scored),
        "prescreen_selected": len(prescreen_all),
    })

    providers_used = sorted({
        p.get("name") or p.get("provider")
        for p in (provider_health or [])
        if p.get("name") or p.get("provider")
    }) or ["yahoo", "tradingview"]

    manifest = HandoffManifest(
        bridge_version=BRIDGE_VERSION,
        workflow_type="EXPLORER",
        workflow_version=WORKFLOW_VERSION,
        generated_at=generated_at,
        analysis_objective="NEXT_WORKING_DAY_DISCOVERY",
        run_mode=config.horizon,
        data_cutoff=generated_at,
        latest_session=latest_session,
        research_data_quality="MIXED",
        execution_grade="NO",
        missing_capabilities=["depth", "trades", "bid_ask_often", "official_egx_calendar"],
        provider_summary={
            "universe_total": counts["UNIVERSE_TOTAL"],
            "equity_universe_total": counts["EQUITY_UNIVERSE_TOTAL"],
            "mapped_symbols": counts["MAPPED_SYMBOLS"],
            "daily_data_available": counts["DAILY_DATA_AVAILABLE"],
            "daily_data_unavailable": counts["DAILY_DATA_UNAVAILABLE"],
            "scanner_eligible_symbols": counts["SCANNER_ELIGIBLE_SYMBOLS"],
            "prescreen_selected": counts["PRESCREEN_SELECTED"],
            "intraday_enriched": counts["INTRADAY_ENRICHED"],
            "handoff_candidates": counts["HANDOFF_CANDIDATES"],
            "latest_completed_market_session": latest_session,
            "target_next_working_day": "UNKNOWN",
            "timing_policy": "NORMALIZED_ONLY_EXCLUDES_LEGACY_UNNORMALIZED",
            "universe_source": uni.get("universe_source"),
            "EXPLORER_COVERAGE": coverage["EXPLORER_COVERAGE"],
            "selection_basis": selection_basis,
            "funnel_status_counts": funnel_coverage,
            "research_data_quality_summary": rdq_summary,
            "execution_grade_summary": exec_summary,
        },
        previous_analysis_status=funnel_coverage,
        ai_mode=AI_CHATGPT_HANDOFF,
        notes=[
            "No paid LLM API",
            "No trading orders",
            "Funnel FV is context-only",
            "Explorer timing/freshness uses NORMALIZED timestamps only",
            "Two-stage: deterministic Stage A shortlist + ChatGPT Stage B",
            "Yahoo daily is the broad-universe source; TradingView is shortlist intraday only",
            "v0.5.1: candidate_score_calibrated is production rank; legacy score is diagnostic",
            "forward_setup_score is HEURISTIC_UNCALIBRATED, not a probability",
            f"scoring_version={SCORING_VERSION} frozen in v0.6",
            "Funnel coverage denominator is EQUITY_UNIVERSE_TOTAL",
        ],
    )
    man = finalize_manifest(manifest, out_root)
    man.update({
        "explorer_version": EXPLORER_VERSION,
        "data_capture_cutoff": generated_at,
        "latest_completed_market_session": latest_session,
        "target_next_working_day_if_known": "UNKNOWN",
        "universe_total": counts["UNIVERSE_TOTAL"],
        "equity_universe_total": counts["EQUITY_UNIVERSE_TOTAL"],
        "mapped_symbols": counts["MAPPED_SYMBOLS"],
        "daily_data_available": counts["DAILY_DATA_AVAILABLE"],
        "daily_data_unavailable": counts["DAILY_DATA_UNAVAILABLE"],
        "scanner_eligible_symbols": counts["SCANNER_ELIGIBLE_SYMBOLS"],
        "prescreen_selected": counts["PRESCREEN_SELECTED"],
        "intraday_enriched": counts["INTRADAY_ENRICHED"],
        "handoff_candidates": counts["HANDOFF_CANDIDATES"],
        "funnel_status_counts": funnel_coverage,
        "research_data_quality_summary": rdq_summary,
        "execution_grade_summary": exec_summary,
        "providers_used": providers_used,
        "environment": environment,
        "coverage": coverage,
        "files_included": man.get("included_files") or [],
        "score_kind": SCORE_KIND,
        "not_a_probability": True,
        "intraday_queried_tickers": enrich_tickers,
        "lane_tops": lane_leaders,
    })
    write_json(out_root / "manifest.json", man)

    zip_path = HERE / "output" / f"EGX_EXPLORER_HANDOFF_{dated}.zip"
    zip_directory(out_root, zip_path, arc_root="EGX_EXPLORER_HANDOFF")

    run_id = None
    if store:
        run_id = store.insert_explorer_run(config.horizon, man)
        for c in candidate_metrics:
            store.insert_explorer_candidate(run_id, c["ticker"], c)

    ws = HERE / "workspace" / "explorer"
    ws.mkdir(parents=True, exist_ok=True)
    write_json(ws / "last_run.json", {
        "zip_path": str(zip_path),
        "package_dir": str(out_root),
        "run_id": run_id,
        "explorer_run_id": explorer_run_id,
        "manifest": man,
        "counts": counts,
        "coverage": coverage,
        "environment": environment,
    })

    if defaulted:
        # Convenience copies for the dashboard (dated dir remains canonical).
        alias_root = HERE / "output" / "explorer_handoff"
        for name in (
            "candidate_metrics.csv", "universe.csv", "universe_summary.json",
            "prescreen_candidates.csv", "prescreen_candidates_calibrated.csv",
            "legacy_vs_calibrated_ranking.csv", "manifest.json", "market_breadth.json",
        ):
            src = out_root / name
            if src.exists():
                shutil.copy2(src, alias_root / name)

    return {
        "package_dir": str(out_root),
        "zip_path": str(zip_path),
        "manifest": man,
        "candidate_count": len(candidate_metrics),
        "funnel_coverage": funnel_coverage,
        "ai_mode": AI_CHATGPT_HANDOFF,
        "orders_generated": False,
        "universe_total": counts["universe_total"],
        "data_eligible_count": counts["data_eligible_count"],
        "scanner_candidate_count": counts["scanner_candidate_count"],
        "handoff_candidate_count": counts["handoff_candidate_count"],
        "DATA_AVAILABLE_SYMBOLS": uni.get("DAILY_DATA_AVAILABLE") or [],
        "DATA_UNAVAILABLE_SYMBOLS": uni.get("DAILY_DATA_UNAVAILABLE") or [],
        "SCANNER_ELIGIBLE_SYMBOLS": uni.get("SCANNER_ELIGIBLE_SYMBOLS") or [],
        "counts": counts,
        "coverage": coverage,
        "environment": environment,
        "correlation_legacy": corr_legacy,
        "correlation_calibrated": corr_calibrated,
        "lane_tops": lane_leaders,
        "intraday_queried_tickers": enrich_tickers,
        "ranked_comparison": ranked_cmp,
        "all_scored_count": len(all_scored),
        "prescreen_all": prescreen_all,
        "scoring_version": SCORING_VERSION,
        "intraday_selection": enrich_sel,
        "snapshot_stats": snap_stats,
        "explorer_run_id": explorer_run_id,
        "market_breadth": market_breadth,
        "candidate_breadth": candidate_breadth,
    }
