"""Import ChatGPT schedule results. Raw text is always preserved. Never writes Fair Value."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re

from egxbridge import __version__ as BRIDGE_VERSION
from egxbridge.analysis.common.models import utc_now, content_hash
from egxbridge.analysis.common.packaging import write_text
from egxbridge.analysis.schedule.types import (
    ANALYSIS_TYPES, ANALYSIS_WEEKLY, SCORING_VERSION, RESULT_ENVELOPE_VERSION,
    LINKAGE_EXPLICIT, LINKAGE_FALLBACK, LINKAGE_AMBIGUOUS, LINKAGE_INVALID, LINKAGE_NOT_LINKED,
    PARSE_VALID, PARSE_INVALID_SCHEMA, PARSE_INVALID_CANONICAL_ID, PARSE_TICKER_MISMATCH,
    PARSE_MISSING_ENVELOPE, PARSE_AMBIGUOUS, PARSE_FALLBACK,
    WEEKLY_METRICS_SOURCE, WEEKLY_INTERPRETATION_SOURCE, APP_OWNED_COUNT_FIELDS,
)
from egxbridge.analysis.schedule.result_schemas import (
    validate_result_envelope, extract_weekly_interpretation, extract_returned_app_counts,
    verify_copied_counts,
)


HERE = Path(__file__).resolve().parents[3]
JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.S | re.I)


def read_source(source: Path | str) -> tuple[str, str]:
    if not isinstance(source, str):
        path = Path(source)
        return path.read_text(encoding="utf-8"), str(path)
    try:
        path = Path(source)
        if path.exists():
            return path.read_text(encoding="utf-8"), str(path)
    except OSError:
        pass
    return str(source), "pasted_text"


def extract_json_envelope(text: str) -> dict[str, Any] | None:
    """Best-effort optional envelope. Invalid JSON never destroys the raw result."""
    try:
        direct = json.loads(text)
        if isinstance(direct, dict):
            return direct
    except (ValueError, TypeError):
        pass
    matches = list(JSON_FENCE.finditer(text or ""))
    blob = None
    if matches:
        blob = matches[-1].group(1)
    else:
        start = (text or "").rfind("{")
        end = (text or "").rfind("}")
        if start >= 0 and end > start:
            blob = text[start:end + 1]
    if not blob:
        return None
    try:
        obj = json.loads(blob)
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _manifest(store) -> dict[str, Any]:
    last = store.latest_schedule_run() if store else None
    if last and last.get("manifest_json"):
        try:
            return json.loads(last["manifest_json"]) or {}
        except Exception:
            return {}
    return {}


def resolve_import_linkage(
    store,
    candidate: dict[str, Any],
    *,
    analysis_type: str,
    schedule_run_id: str | None,
) -> dict[str, Any]:
    """Link a ChatGPT candidate to a canonical signal. Never guess among multiples."""
    ticker = str(candidate.get("ticker") or "").upper()
    explicit = (candidate.get("canonical_signal_id") or "").strip() or None
    if explicit:
        row = store.get_canonical_signal(explicit)
        if not row:
            return {
                "linkage_method": LINKAGE_INVALID,
                "canonical_signal_id": None,
                "reason": "canonical_signal_id_not_found",
            }
        if str(row.get("ticker") or "").upper() != ticker:
            return {
                "linkage_method": LINKAGE_INVALID,
                "canonical_signal_id": None,
                "reason": "ticker_mismatch",
                "canonical_ticker": row.get("ticker"),
            }
        return {
            "linkage_method": LINKAGE_EXPLICIT,
            "canonical_signal_id": explicit,
            "signal_family_id": row.get("signal_family_id") or (row.get("payload") or {}).get("signal_family_id"),
            "parent_signal_id": row.get("parent_signal_id") or (row.get("payload") or {}).get("parent_signal_id"),
            "market_state_fingerprint": row.get("market_state_fingerprint") or (row.get("payload") or {}).get("market_state_fingerprint"),
            "explorer_run_id": row.get("explorer_run_id"),
            "signal_origin": row.get("signal_origin"),
        }

    obs = store.list_analysis_observations(ticker=ticker)
    matches = [
        o for o in obs
        if o.get("analysis_type") == analysis_type
        and (o.get("generated_by") or "LOCAL") == "LOCAL"
        and (not schedule_run_id or o.get("schedule_run_id") == schedule_run_id)
    ]
    cids = list(dict.fromkeys(o.get("canonical_signal_id") for o in matches if o.get("canonical_signal_id")))
    if len(cids) == 1:
        row = store.get_canonical_signal(cids[0]) or {}
        local = matches[0]
        return {
            "linkage_method": LINKAGE_FALLBACK,
            "canonical_signal_id": cids[0],
            "local_observation_id": local.get("analysis_observation_id"),
            "signal_family_id": (local.get("payload") or {}).get("signal_family_id") or row.get("signal_family_id"),
            "parent_signal_id": (local.get("payload") or {}).get("parent_signal_id") or row.get("parent_signal_id"),
            "market_state_fingerprint": (local.get("payload") or {}).get("market_state_fingerprint") or row.get("market_state_fingerprint"),
            "explorer_run_id": local.get("explorer_run_id") or row.get("explorer_run_id"),
            "signal_origin": (local.get("payload") or {}).get("signal_origin") or row.get("signal_origin"),
        }
    if len(cids) > 1:
        return {
            "linkage_method": LINKAGE_AMBIGUOUS,
            "canonical_signal_id": None,
            "reason": "multiple_canonical_signals_for_ticker_context",
            "candidate_canonical_ids": cids,
        }
    return {
        "linkage_method": LINKAGE_NOT_LINKED,
        "canonical_signal_id": None,
        "reason": "no_unambiguous_match",
    }


def canonical_validation_for_link(link: dict[str, Any]) -> str:
    method = link.get("linkage_method")
    reason = link.get("reason")
    if method == LINKAGE_INVALID:
        if reason == "ticker_mismatch":
            return PARSE_TICKER_MISMATCH
        return PARSE_INVALID_CANONICAL_ID
    if method == LINKAGE_FALLBACK:
        return PARSE_FALLBACK
    if method == LINKAGE_AMBIGUOUS:
        return PARSE_AMBIGUOUS
    if method == LINKAGE_EXPLICIT:
        return LINKAGE_EXPLICIT
    return LINKAGE_NOT_LINKED


def _package_context(store) -> dict[str, Any]:
    man = _manifest(store)
    return {
        "session_phase": man.get("session_phase"),
        "live_session_evidence_available": man.get("live_session_evidence_available"),
        "run_id": man.get("run_id"),
        "scanner_sample_n": man.get("scanner_sample_n"),
        "canonical_signals_n": man.get("canonical_signals_n"),
        "analysis_observations_generated_n": man.get("analysis_observations_generated_n"),
        "analysis_observations_imported_n": man.get("analysis_observations_imported_n"),
        "analysis_observations_evaluable_n": man.get("analysis_observations_evaluable_n"),
        "analysis_observations_n": man.get("analysis_observations_n"),
    }


def _app_weekly_metrics(store) -> dict[str, Any]:
    pkg = _package_context(store)
    metrics = {k: pkg.get(k) for k in APP_OWNED_COUNT_FIELDS if pkg.get(k) is not None}
    last = store.latest_schedule_run() if store else None
    if last and last.get("package_dir"):
        hist_path = Path(last["package_dir"]) / "optional" / "calibration_history_summary.json"
        if hist_path.exists():
            try:
                hist = json.loads(hist_path.read_text(encoding="utf-8"))
            except Exception:
                hist = {}
            for k in APP_OWNED_COUNT_FIELDS:
                if k in hist:
                    metrics[k] = hist[k]
    return metrics


def import_schedule_result(
    source: Path | str,
    *,
    analysis_type: str,
    run_id: str | None = None,
    store=None,
    latest_market_session: str | None = None,
    raw_dest_dir: Path | None = None,
    package_session_phase: str | None = None,
    package_live_session_evidence_available: bool | None = None,
) -> dict[str, Any]:
    if analysis_type not in ANALYSIS_TYPES:
        raise ValueError(f"Unknown analysis_type: {analysis_type}")
    content, source_file = read_source(source)
    h = content_hash(content)
    dest_dir = Path(raw_dest_dir) if raw_dest_dir else HERE / "workspace" / "schedule" / "imports"
    dest_dir.mkdir(parents=True, exist_ok=True)
    raw_path = dest_dir / f"{analysis_type}_{h[:12]}.md"
    write_text(raw_path, content)  # original unchanged — always preserved
    envelope = extract_json_envelope(content)
    pkg = _package_context(store) if store else {}
    phase = package_session_phase if package_session_phase is not None else pkg.get("session_phase")
    live_flag = (
        package_live_session_evidence_available
        if package_live_session_evidence_available is not None
        else pkg.get("live_session_evidence_available")
    )
    schema_check = validate_result_envelope(
        envelope,
        expected_analysis_type=analysis_type,
        package_session_phase=phase,
        package_live_session_evidence_available=live_flag,
    )
    rid = (
        run_id
        or (envelope or {}).get("schedule_run_id")
        or (envelope or {}).get("run_id")
        or pkg.get("run_id")
    )
    result_id = content_hash(f"{analysis_type}|{rid or ''}|{h}")[:40]
    env_ver = (envelope or {}).get("result_envelope_version") or RESULT_ENVELOPE_VERSION
    rec = {
        "analysis_result_id": result_id,
        "analysis_type": analysis_type,
        "run_id": rid,
        "generated_by": "CHATGPT_HANDOFF",
        "imported_at": utc_now(),
        "analysis_timestamp": utc_now(),
        "latest_market_session": latest_market_session or (envelope or {}).get("market_session_basis"),
        "source_content_hash": h,
        "raw_result_path": str(raw_path),
        "source_file": source_file,
        "content_text": content,
        "envelope": envelope,
        "scoring_version": SCORING_VERSION,
        "bridge_version": BRIDGE_VERSION,
        "result_envelope_version": env_ver,
        "modifies_funnel_fair_value": False,
        "orders_generated": False,
        "remote_llm_call": False,
    }
    linkages: list[dict[str, Any]] = []
    forward_import_issues = []
    accept_structured = schema_check["structured_parse_status"] not in {
        PARSE_INVALID_SCHEMA, PARSE_MISSING_ENVELOPE,
    }
    live_valid = bool(schema_check.get("live_state_analysis_valid"))
    app_weekly = _app_weekly_metrics(store) if store and analysis_type == ANALYSIS_WEEKLY else {}
    weekly_interpretation = extract_weekly_interpretation(envelope) if analysis_type == ANALYSIS_WEEKLY else {}
    weekly_returned = extract_returned_app_counts(envelope) if analysis_type == ANALYSIS_WEEKLY else {}
    weekly_count_mismatches = verify_copied_counts(weekly_returned, app_weekly) if analysis_type == ANALYSIS_WEEKLY else []
    if store:
        store.insert_schedule_import(rec)
        from egxbridge.analysis.schedule.identity import observation_record, analysis_observation_id
        if accept_structured:
            for c in (envelope or {}).get("candidates") or []:
                if not isinstance(c, dict):
                    continue
                store.insert_candidate_state({
                    "analysis_result_id": result_id,
                    "ticker": c.get("ticker"),
                    "analysis_type": analysis_type,
                    "catalyst_status": c.get("catalyst_status"),
                    "next_session_status": c.get("status") or c.get("next_session_status"),
                    "setup_state": c.get("SETUP_STATE") or c.get("setup_state"),
                    "funnel_action": c.get("FUNNEL_ACTION") or c.get("funnel_action"),
                    "payload": c,
                })
                link = resolve_import_linkage(
                    store, c, analysis_type=analysis_type, schedule_run_id=rid,
                )
                link["ticker"] = str(c.get("ticker") or "").upper()
                link["canonical_validation"] = canonical_validation_for_link(link)
                linkages.append(link)
                if not link.get("canonical_signal_id"):
                    continue
                if not live_valid:
                    continue
                extra = {
                    "chatgpt_status": c.get("status") or c.get("next_session_status"),
                    "catalyst_status": c.get("catalyst_status"),
                    "setup_state": c.get("SETUP_STATE") or c.get("setup_state"),
                    "funnel_action": c.get("FUNNEL_ACTION") or c.get("funnel_action"),
                    "next_session_status": c.get("status") or c.get("next_session_status"),
                    "imported_at": rec.get("imported_at"),
                    "analysis_result_id": result_id,
                    "linkage_method": link["linkage_method"],
                    "canonical_validation": link["canonical_validation"],
                    "import_status": "IMPORTED",
                    "result_envelope_version": env_ver,
                    "session_phase_validation": schema_check.get("session_phase_validation"),
                    "market_state_fingerprint": link.get("market_state_fingerprint") or c.get("market_state_fingerprint"),
                }
                ident = {
                    "canonical_signal_id": link["canonical_signal_id"],
                    "explorer_run_id": link.get("explorer_run_id"),
                    "signal_family_id": link.get("signal_family_id") or c.get("signal_family_id"),
                    "parent_signal_id": link.get("parent_signal_id") if link.get("parent_signal_id") is not None else c.get("parent_signal_id"),
                    "signal_origin": link.get("signal_origin"),
                    "market_state_fingerprint": extra["market_state_fingerprint"],
                }
                local_oid = link.get("local_observation_id") or analysis_observation_id(
                    canonical_id=ident["canonical_signal_id"],
                    analysis_type=analysis_type,
                    schedule_run_id=rid,
                    generated_by="LOCAL",
                )
                store.update_analysis_observation_import({
                    "analysis_observation_id": local_oid,
                    "canonical_signal_id": ident["canonical_signal_id"],
                    "analysis_type": analysis_type,
                    "ticker": c.get("ticker"),
                    "schedule_run_id": rid,
                    "explorer_run_id": ident.get("explorer_run_id"),
                    "generated_by": "LOCAL",
                    **extra,
                    "import_status": "GENERATED",
                })
                chat_obs = observation_record(
                    identity=ident,
                    analysis_type=analysis_type,
                    ticker=c.get("ticker") or "",
                    environment=store.environment,
                    analysis_timestamp=rec.get("imported_at"),
                    schedule_run_id=rid,
                    generated_by="CHATGPT_HANDOFF",
                    extra=extra,
                )
                store.insert_analysis_observation(chat_obs)
                from egxbridge.analysis.forward_validation import append_classification, append_later_review
                try:
                    if analysis_type == ANALYSIS_WEEKLY:
                        append_later_review(store, ident["canonical_signal_id"], ticker=c["ticker"],
                            fields=c.get("later_event_review") or c, source_id=result_id,
                            cutoff=c.get("event_source_cutoff") or (envelope or {}).get("declared_research_cutoff"))
                    else:
                        append_classification(store, ident["canonical_signal_id"], ticker=c["ticker"],
                            fields=c.get("funnel_v28") or c, source="SCHEDULE_LLM", source_id=result_id,
                            imported_at=rec["imported_at"],
                            source_cutoff=c.get("declared_research_cutoff") or (envelope or {}).get("declared_research_cutoff"),
                            schedule_version=env_ver, funnel_version=c.get("funnel_version"),
                            analysis_started_at=(envelope or {}).get("analysis_started_at"),
                            market_data_cutoff=(envelope or {}).get("market_data_cutoff"),
                            observation_id=chat_obs["analysis_observation_id"], schedule_status=extra["chatgpt_status"])
                except ValueError as exc:
                    forward_import_issues.append(str(exc))
            if analysis_type == ANALYSIS_WEEKLY:
                from egxbridge.analysis.forward_validation import store_change_proposal
                for proposal in (envelope or {}).get("rule_change_proposals") or []:
                    try:
                        store_change_proposal(store, proposal, source="WEEKLY_LLM", source_id=result_id)
                    except (ValueError, TypeError) as exc:
                        forward_import_issues.append(str(exc))
        if live_valid and accept_structured:
            try:
                from egxbridge.analysis.schedule.decisions import refresh_daily_decision_from_store
                last = store.latest_schedule_run()
                cands: list[dict[str, Any]] = []
                pkg_dir = Path((last or {}).get("package_dir") or "")
                snap_path = pkg_dir / "common" / "explorer_snapshot.json"
                if snap_path.exists():
                    snap = json.loads(snap_path.read_text(encoding="utf-8"))
                    cands = list(snap.get("candidates") or [])
                if cands:
                    refresh_daily_decision_from_store(
                        store,
                        date_tag=(latest_market_session or rec.get("imported_at") or utc_now())[:10],
                        run_id=rid or (last or {}).get("run_id") or "",
                        latest_session=latest_market_session or rec.get("latest_market_session"),
                        candidates=cands,
                    )
            except Exception:
                pass
    parse_status = schema_check["structured_parse_status"]
    if parse_status == PARSE_VALID:
        validations = [l.get("canonical_validation") for l in linkages]
        if PARSE_INVALID_CANONICAL_ID in validations:
            parse_status = PARSE_INVALID_CANONICAL_ID
        elif PARSE_TICKER_MISMATCH in validations:
            parse_status = PARSE_TICKER_MISMATCH
    return {
        "analysis_result_id": result_id,
        "analysis_type": analysis_type,
        "run_id": rid,
        "saved_path": str(raw_path),
        "content_hash": h,
        "original_preserved": True,
        "envelope_parsed": envelope is not None,
        "envelope": envelope,
        "result_envelope_version": env_ver,
        "candidate_linkages": linkages,
        "structured_parse_status": parse_status,
        "session_phase_validation": schema_check.get("session_phase_validation"),
        "live_state_analysis_valid": live_valid,
        "schema_issues": (schema_check.get("issues") or []) + forward_import_issues,
        "weekly_metrics": app_weekly if analysis_type == ANALYSIS_WEEKLY else None,
        "weekly_metrics_source": WEEKLY_METRICS_SOURCE if analysis_type == ANALYSIS_WEEKLY else None,
        "weekly_interpretation": weekly_interpretation if analysis_type == ANALYSIS_WEEKLY else None,
        "weekly_interpretation_source": WEEKLY_INTERPRETATION_SOURCE if analysis_type == ANALYSIS_WEEKLY else None,
        "weekly_count_mismatches": weekly_count_mismatches,
        "modifies_funnel_fair_value": False,
        "orders_generated": False,
        "remote_llm_call": False,
    }
