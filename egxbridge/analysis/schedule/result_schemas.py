"""Job-specific ChatGPT result envelopes. Does not change scoring or identity hashing."""
from __future__ import annotations

from typing import Any

from egxbridge.analysis.funnel.schema import result_schema as funnel_result_schema

from egxbridge.analysis.schedule.types import (
    ANALYSIS_MACRO, ANALYSIS_PREMARKET, ANALYSIS_INTRADAY, ANALYSIS_VALUE, ANALYSIS_WEEKLY,
    ANALYSIS_TYPES, RESULT_SCHEMA_FILES,
    RESULT_ENVELOPE_VERSION, HANDOFF_SCHEMA_VERSION, SUPPORTED_RESULT_ENVELOPE_VERSION,
    SCORING_VERSION,
    PARSE_VALID, PARSE_INVALID_SCHEMA, PARSE_NEEDS_REVIEW, PARSE_MISSING_ENVELOPE,
    PHASE_MATCH, PHASE_MISMATCH, PHASE_MISSING,
    STALE_EVIDENCE_PHASES, NOT_LIVE_CONFIRMATION_TEXT, APP_OWNED_COUNT_FIELDS,
    IDENTITY_FIELDS, ANALYSIS_OBSERVATIONS_N_SEMANTICS, DEPRECATED_FIELDS,
    WEEKLY_METRICS_SOURCE, WEEKLY_INTERPRETATION_SOURCE,
)


COPY_FROM_PACKAGE = "<COPY_FROM_PACKAGE>"
COPY_FROM_INPUT = "<COPY_FROM_INPUT>"
MODEL_DECISION = "<MODEL_DECISION>"
OPTIONAL = "<OPTIONAL>"
PLACEHOLDERS = {COPY_FROM_PACKAGE, COPY_FROM_INPUT, MODEL_DECISION, OPTIONAL}

CONFIDENCE_VALUES = ("LOW", "MEDIUM", "HIGH")

# Result-envelope enums. NOT_RELIABLE is allowed on handoff labels; scoring sets stay frozen.
CATALYST_STATUS_VALUES = (
    "POSITIVE_CONFIRMED", "POSITIVE_UNVERIFIED", "NEUTRAL",
    "NEGATIVE_CONFIRMED", "NEGATIVE_UNVERIFIED", "NO_MATERIAL_CATALYST_FOUND",
    "NOT_RELIABLE",
)
NEXT_SESSION_STATUS_VALUES = (
    "PROMOTE", "KEEP", "DOWNGRADE", "REMOVE", "WATCH_ONLY", "NOT_RELIABLE",
)
SETUP_STATE_VALUES = (
    "NOT_STARTED", "EARLY_CONFIRMATION", "CONFIRMED", "PARTIAL_CONFIRMATION",
    "FAILED", "REJECTED_BREAKOUT", "RECLAIM", "OVEREXTENDED", "NO_TRADE", "NOT_RELIABLE",
)
FUNNEL_ACTION_VALUES = (
    "NO_ACTION", "CONTINUE_FUNNEL", "START_FULL_FUNNEL", "RUN_DELTA",
    "REVIEW_EXISTING_FUNNEL", "NOT_RELIABLE",
)
MARKET_REGIME_VALUES = ("RISK_ON", "NEUTRAL", "RISK_OFF", "MIXED", "NOT_RELIABLE")
PORTFOLIO_POSTURE_VALUES = ("NORMAL", "SELECTIVE", "DEFENSIVE", "NO_NEW_RISK", "NOT_RELIABLE")
CALIBRATION_STATUS_VALUES = (
    "INSUFFICIENT_SAMPLE", "EARLY_SAMPLE", "DEVELOPING", "USABLE", "NOT_RELIABLE",
)
SESSION_PHASE_VALUES = (
    "PRE_OPEN", "CONTINUOUS_TRADING", "CLOSING_AUCTION", "TRADING_AT_LAST", "POST_CLOSE", "UNKNOWN",
)

COMMON_ENVELOPE_FIELDS = (
    "result_envelope_version",
    "analysis_type",
    "schedule_run_id",
    "explorer_run_id",
    "generated_from_package_id",
    "market_session_basis",
    "session_phase",
    "analysis_timestamp",
    "notes",
)

CANDIDATE_IDENTITY_FIELDS = IDENTITY_FIELDS

JOB_ENUMS: dict[str, dict[str, tuple[str, ...]]] = {
    ANALYSIS_PREMARKET: {
        "catalyst_status": CATALYST_STATUS_VALUES,
        "next_session_status": NEXT_SESSION_STATUS_VALUES,
        "confidence": CONFIDENCE_VALUES,
    },
    ANALYSIS_INTRADAY: {
        "setup_state": SETUP_STATE_VALUES,
        "confidence": CONFIDENCE_VALUES,
    },
    ANALYSIS_VALUE: {
        "funnel_action": FUNNEL_ACTION_VALUES,
        "confidence": CONFIDENCE_VALUES,
    },
    ANALYSIS_MACRO: {
        "market_regime": MARKET_REGIME_VALUES,
        "portfolio_posture": PORTFOLIO_POSTURE_VALUES,
        "confidence": CONFIDENCE_VALUES,
    },
    ANALYSIS_WEEKLY: {
        "calibration_status": CALIBRATION_STATUS_VALUES,
    },
}

CANDIDATE_ENUM_FIELDS = {
    ANALYSIS_PREMARKET: {
        "catalyst_status": CATALYST_STATUS_VALUES,
        "next_session_status": NEXT_SESSION_STATUS_VALUES,
        "status": NEXT_SESSION_STATUS_VALUES,
        "confidence": CONFIDENCE_VALUES,
    },
    ANALYSIS_INTRADAY: {
        "setup_state": SETUP_STATE_VALUES,
        "SETUP_STATE": SETUP_STATE_VALUES,
        "confidence": CONFIDENCE_VALUES,
    },
    ANALYSIS_VALUE: {
        "funnel_action": FUNNEL_ACTION_VALUES,
        "FUNNEL_ACTION": FUNNEL_ACTION_VALUES,
        "confidence": CONFIDENCE_VALUES,
    },
}

JOB_LEVEL_ENUM_FIELDS = {
    ANALYSIS_MACRO: {
        "market_regime": MARKET_REGIME_VALUES,
        "MARKET_REGIME": MARKET_REGIME_VALUES,
        "portfolio_posture": PORTFOLIO_POSTURE_VALUES,
        "PORTFOLIO_POSTURE": PORTFOLIO_POSTURE_VALUES,
        "confidence": CONFIDENCE_VALUES,
    },
    ANALYSIS_WEEKLY: {
        "calibration_status": CALIBRATION_STATUS_VALUES,
        "CALIBRATION_STATUS": CALIBRATION_STATUS_VALUES,
    },
    ANALYSIS_INTRADAY: {
        "session_phase": SESSION_PHASE_VALUES,
    },
}

WEEKLY_INTERPRETATION_FIELDS = (
    "scanner_summary",
    "analysis_value_add_summary",
    "false_positive_notes",
    "missed_opportunity_notes",
    "calibration_status",
    "notes",
    "confidence",
)


def is_placeholder(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    return text in PLACEHOLDERS or (text.startswith("<") and text.endswith(">"))


def enum_line(name: str, values: tuple[str, ...]) -> str:
    return f"{name} = " + " | ".join(values)


def _common_field_docs() -> dict[str, Any]:
    return {
        "result_envelope_version": {"required": True, "const": RESULT_ENVELOPE_VERSION},
        "analysis_type": {"required": True},
        "schedule_run_id": {"required": True, "copy": COPY_FROM_PACKAGE},
        "explorer_run_id": {"required": False, "copy": COPY_FROM_PACKAGE},
        "generated_from_package_id": {"required": False, "copy": COPY_FROM_PACKAGE},
        "market_session_basis": {"required": False, "copy": COPY_FROM_PACKAGE},
        "session_phase": {
            "required": True,
            "enum": list(SESSION_PHASE_VALUES),
            "copy": COPY_FROM_PACKAGE,
            "note": "Must inherit the package session_phase. Never hard-code CONTINUOUS_TRADING.",
        },
        "analysis_timestamp": {"required": False, "copy": COPY_FROM_PACKAGE},
        "notes": {"required": False},
    }


def _identity_field_docs() -> dict[str, Any]:
    return {
        "ticker": {"required_when_candidate_present": True},
        "canonical_signal_id": {
            "required_when_candidate_present": True,
            "note": "Ticker alone is not the identity key.",
        },
        "signal_family_id": {"required_when_candidate_present": True, "copy": COPY_FROM_PACKAGE},
        "parent_signal_id": {"required_when_candidate_present": True, "copy": COPY_FROM_PACKAGE},
        "market_state_fingerprint": {"required_when_candidate_present": True, "copy": COPY_FROM_PACKAGE},
    }


def _template_identity() -> dict[str, Any]:
    return {
        "ticker": COPY_FROM_PACKAGE,
        "canonical_signal_id": COPY_FROM_PACKAGE,
        "signal_family_id": COPY_FROM_PACKAGE,
        "parent_signal_id": COPY_FROM_PACKAGE,
        "market_state_fingerprint": COPY_FROM_PACKAGE,
    }


def _package_phase(ctx: dict[str, Any] | None) -> str:
    sess = (ctx or {}).get("session_meta") or {}
    phase = sess.get("session_phase") or (ctx or {}).get("session_phase")
    return str(phase or COPY_FROM_PACKAGE)


def _live_evidence(ctx: dict[str, Any] | None) -> bool | str:
    if ctx and "live_session_evidence_available" in ctx:
        return bool(ctx.get("live_session_evidence_available"))
    return False


def common_example_fields(analysis_type: str, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = ctx or {}
    return {
        "result_envelope_version": RESULT_ENVELOPE_VERSION,
        "analysis_type": analysis_type,
        "schedule_run_id": COPY_FROM_PACKAGE,
        "explorer_run_id": COPY_FROM_PACKAGE,
        "generated_from_package_id": COPY_FROM_PACKAGE,
        "market_session_basis": COPY_FROM_PACKAGE,
        "session_phase": _package_phase(ctx),
        "analysis_timestamp": COPY_FROM_PACKAGE,
        "analysis_started_at": OPTIONAL,
        "declared_research_cutoff": OPTIONAL,
        "market_data_cutoff": COPY_FROM_PACKAGE,
        "notes": OPTIONAL,
        "scoring_version_observed": SCORING_VERSION,
        "example_kind": "TEMPLATE_NOT_ACTUAL_OUTPUT",
    }


def build_example_envelope(analysis_type: str, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = ctx or {}
    example = common_example_fields(analysis_type, ctx)
    if analysis_type == ANALYSIS_MACRO:
        example.update({
            "market_regime": MODEL_DECISION,
            "portfolio_posture": MODEL_DECISION,
            "macro_drivers": OPTIONAL,
            "market_breadth_interpretation": OPTIONAL,
            "risk_factors": OPTIONAL,
            "confidence": MODEL_DECISION,
            "candidates": OPTIONAL,
            "candidate_records_required": False,
        })
    elif analysis_type == ANALYSIS_PREMARKET:
        example["candidates"] = [{
            **_template_identity(),
            "catalyst_status": MODEL_DECISION,
            "next_session_status": MODEL_DECISION,
            "confidence": MODEL_DECISION,
            "catalyst_summary": OPTIONAL,
            "source_summary": OPTIONAL,
            "risk_notes": OPTIONAL,
        }]
        example["catalyst_status_required"] = False
        example["catalyst_status_note"] = "Do not make catalyst_status mandatory if no evidence exists."
    elif analysis_type == ANALYSIS_INTRADAY:
        live = _live_evidence(ctx)
        example["live_session_evidence_available"] = live
        if live is False:
            example["live_confirmation_note"] = NOT_LIVE_CONFIRMATION_TEXT
        example["candidates"] = [{
            **_template_identity(),
            "setup_state": MODEL_DECISION,
            "confirmation_notes": OPTIONAL,
            "risk_notes": OPTIONAL,
            "confidence": MODEL_DECISION,
        }]
    elif analysis_type == ANALYSIS_VALUE:
        example["does_not_recalculate_fair_value"] = True
        example["does_not_overwrite_funnel_valuation"] = True
        example["candidates"] = [{
            **_template_identity(),
            "funnel_action": MODEL_DECISION,
            "reason": OPTIONAL,
            "material_new_evidence": OPTIONAL,
            "confidence": MODEL_DECISION,
        }]
    elif analysis_type == ANALYSIS_WEEKLY:
        example.update({
            "scanner_summary": MODEL_DECISION,
            "analysis_value_add_summary": MODEL_DECISION,
            "false_positive_notes": OPTIONAL,
            "missed_opportunity_notes": OPTIONAL,
            "calibration_status": MODEL_DECISION,
            "candidate_records_required": False,
            "weekly_metrics": WEEKLY_METRICS_SOURCE,
            "weekly_interpretation": WEEKLY_INTERPRETATION_SOURCE,
            "deterministic_counts": {
                "ownership": WEEKLY_METRICS_SOURCE,
                "if_copied_use": COPY_FROM_INPUT,
                "chatgpt_is_not_authoritative": True,
                "fields": list(APP_OWNED_COUNT_FIELDS),
            },
        })
    return example


def build_job_schema(analysis_type: str, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    if analysis_type not in ANALYSIS_TYPES:
        raise ValueError(f"Unknown analysis_type: {analysis_type}")
    schema: dict[str, Any] = {
        "schema_name": RESULT_SCHEMA_FILES[analysis_type],
        "handoff_schema_version": HANDOFF_SCHEMA_VERSION,
        "result_envelope_version": RESULT_ENVELOPE_VERSION,
        "supported_result_envelope_version": SUPPORTED_RESULT_ENVELOPE_VERSION,
        "scoring_version": SCORING_VERSION,
        "analysis_type": analysis_type,
        "example_kind": "TEMPLATE_NOT_ACTUAL_OUTPUT",
        "common_envelope_fields": _common_field_docs(),
        "candidate_identity_fields": _identity_field_docs(),
        "ticker_is_not_identity_key": True,
        "deprecated_fields": list(DEPRECATED_FIELDS),
        "analysis_observations_n_semantics": ANALYSIS_OBSERVATIONS_N_SEMANTICS,
        "enums": {k: list(v) for k, v in JOB_ENUMS.get(analysis_type, {}).items()},
        "example": build_example_envelope(analysis_type, ctx),
        "optional_funnel_v28": funnel_result_schema(),
        "optional_cutoffs": ["analysis_started_at", "declared_research_cutoff", "market_data_cutoff"],
    }
    if analysis_type == ANALYSIS_MACRO:
        schema.update({
            "candidate_records_required": False,
            "job_level_fields": {
                "market_regime": list(MARKET_REGIME_VALUES),
                "portfolio_posture": list(PORTFOLIO_POSTURE_VALUES),
                "macro_drivers": "optional",
                "market_breadth_interpretation": "optional",
                "risk_factors": "optional",
                "confidence": list(CONFIDENCE_VALUES),
            },
            "note": "Macro is valid without per-candidate records. Canonical identity is required only when candidate records are included.",
        })
    elif analysis_type == ANALYSIS_PREMARKET:
        schema.update({
            "candidate_records_required": True,
            "per_candidate_fields": {
                **{k: COPY_FROM_PACKAGE for k in CANDIDATE_IDENTITY_FIELDS},
                "catalyst_status": {
                    "enum": list(CATALYST_STATUS_VALUES),
                    "required": False,
                    "note": "Not mandatory if no evidence exists.",
                },
                "next_session_status": list(NEXT_SESSION_STATUS_VALUES),
                "confidence": list(CONFIDENCE_VALUES),
                "catalyst_summary": "optional",
                "source_summary": "optional",
                "risk_notes": "optional",
            },
        })
    elif analysis_type == ANALYSIS_INTRADAY:
        schema.update({
            "candidate_records_required": True,
            "primary_decision_field": "setup_state",
            "do_not_use_premarket_fields_as_primary": True,
            "live_session_evidence_available": {"type": "boolean"},
            "stale_evidence_phases": sorted(STALE_EVIDENCE_PHASES),
            "not_live_confirmation_text": NOT_LIVE_CONFIRMATION_TEXT,
            "per_candidate_fields": {
                **{k: COPY_FROM_PACKAGE for k in CANDIDATE_IDENTITY_FIELDS},
                "setup_state": list(SETUP_STATE_VALUES),
                "confirmation_notes": "optional",
                "risk_notes": "optional",
                "confidence": list(CONFIDENCE_VALUES),
            },
        })
    elif analysis_type == ANALYSIS_VALUE:
        schema.update({
            "candidate_records_required": True,
            "does_not_recalculate_fair_value": True,
            "does_not_overwrite_funnel_valuation": True,
            "per_candidate_fields": {
                **{k: COPY_FROM_PACKAGE for k in CANDIDATE_IDENTITY_FIELDS},
                "funnel_action": list(FUNNEL_ACTION_VALUES),
                "reason": "optional",
                "material_new_evidence": "optional",
                "confidence": list(CONFIDENCE_VALUES),
            },
            "forbidden_fields": ["fair_value", "Fair Value", "Fair Value Range"],
        })
    elif analysis_type == ANALYSIS_WEEKLY:
        schema.update({
            "candidate_records_required": False,
            "job_level_fields": {
                "scanner_summary": "interpretation",
                "analysis_value_add_summary": "interpretation",
                "false_positive_notes": "optional",
                "missed_opportunity_notes": "optional",
                "calibration_status": list(CALIBRATION_STATUS_VALUES),
            },
            "weekly_metrics": WEEKLY_METRICS_SOURCE,
            "weekly_interpretation": WEEKLY_INTERPRETATION_SOURCE,
            "app_owned_deterministic_fields": {
                "ownership": WEEKLY_METRICS_SOURCE,
                "chatgpt_role": "INTERPRET_ONLY",
                "if_returned_use": COPY_FROM_INPUT,
                "do_not_hard_code_zeros": True,
                "fields": list(APP_OWNED_COUNT_FIELDS),
            },
            "note": "Weekly X-Ray may return only aggregate interpretation. Canonical identity is required only when per-candidate audit records are present. Do not ask ChatGPT to recreate deterministic counts unless COPY_FROM_INPUT.",
        })
    return schema


def build_all_job_schemas(ctx: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    return {job: build_job_schema(job, ctx) for job in ANALYSIS_TYPES}


def result_schema_index(ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "handoff_schema_version": HANDOFF_SCHEMA_VERSION,
        "result_envelope_version": RESULT_ENVELOPE_VERSION,
        "supported_result_envelope_version": SUPPORTED_RESULT_ENVELOPE_VERSION,
        "scoring_version": SCORING_VERSION,
        "note": "Job-specific schemas live in common/schemas/. This index is not a PREMARKET example.",
        "deprecated_fields": list(DEPRECATED_FIELDS),
        "analysis_observations_n_semantics": ANALYSIS_OBSERVATIONS_N_SEMANTICS,
        "result_schemas": {
            job: f"common/schemas/{fname}" for job, fname in RESULT_SCHEMA_FILES.items()
        },
    }


def markdown_enum_block(analysis_type: str) -> str:
    enums = JOB_ENUMS.get(analysis_type) or {}
    lines = []
    for name, values in enums.items():
        lines.append(enum_line(name, values))
    return "\n".join(lines)


def extract_weekly_interpretation(envelope: dict[str, Any] | None) -> dict[str, Any]:
    if not envelope:
        return {}
    out = {k: envelope.get(k) for k in WEEKLY_INTERPRETATION_FIELDS if k in envelope}
    if envelope.get("candidates"):
        out["candidates"] = envelope.get("candidates")
    return out


def extract_returned_app_counts(envelope: dict[str, Any] | None) -> dict[str, Any]:
    if not envelope:
        return {}
    out = {}
    for k in APP_OWNED_COUNT_FIELDS:
        if k in envelope and not is_placeholder(envelope.get(k)):
            out[k] = envelope.get(k)
    nested = envelope.get("deterministic_counts")
    if isinstance(nested, dict):
        for k in APP_OWNED_COUNT_FIELDS:
            if k in nested and not is_placeholder(nested.get(k)) and k not in out:
                out[k] = nested.get(k)
    return out


def verify_copied_counts(returned: dict[str, Any], app_metrics: dict[str, Any] | None) -> list[dict[str, Any]]:
    app_metrics = app_metrics or {}
    mismatches = []
    for k, v in returned.items():
        if k not in app_metrics:
            continue
        if app_metrics.get(k) != v:
            mismatches.append({
                "field": k,
                "chatgpt_value": v,
                "app_value": app_metrics.get(k),
                "authoritative": WEEKLY_METRICS_SOURCE,
            })
    return mismatches


def _enum_ok(value: Any, allowed: tuple[str, ...] | list[str] | set[str]) -> bool:
    if value is None or is_placeholder(value):
        return True
    return str(value).strip().upper() in {str(x).upper() for x in allowed}


def validate_result_envelope(
    envelope: dict[str, Any] | None,
    *,
    expected_analysis_type: str,
    package_session_phase: str | None = None,
    package_live_session_evidence_available: bool | None = None,
) -> dict[str, Any]:
    """Schema/type/phase checks. Does not rewrite ChatGPT fields."""
    issues: list[str] = []
    if envelope is None:
        return {
            "structured_parse_status": PARSE_MISSING_ENVELOPE,
            "session_phase_validation": PHASE_MISSING,
            "live_state_analysis_valid": False,
            "issues": ["no_json_envelope"],
            "analysis_type_ok": False,
        }

    returned_type = envelope.get("analysis_type")
    analysis_type_ok = True
    status = PARSE_VALID
    if returned_type:
        if str(returned_type) != expected_analysis_type:
            analysis_type_ok = False
            status = PARSE_INVALID_SCHEMA
            issues.append(
                f"analysis_type {returned_type} does not match expected {expected_analysis_type}"
            )
    env_ver = envelope.get("result_envelope_version")
    if env_ver and str(env_ver) != RESULT_ENVELOPE_VERSION and not is_placeholder(env_ver):
        issues.append(f"result_envelope_version {env_ver} != {RESULT_ENVELOPE_VERSION}")

    job_type = expected_analysis_type
    for field, allowed in (JOB_LEVEL_ENUM_FIELDS.get(job_type) or {}).items():
        if field in envelope and not _enum_ok(envelope.get(field), allowed):
            status = PARSE_INVALID_SCHEMA
            issues.append(f"invalid job-level enum {field}={envelope.get(field)!r}")

    cand_enums = CANDIDATE_ENUM_FIELDS.get(job_type) or {}
    for cand in envelope.get("candidates") or []:
        if not isinstance(cand, dict):
            continue
        for field, allowed in cand_enums.items():
            if field in cand and not _enum_ok(cand.get(field), allowed):
                status = PARSE_INVALID_SCHEMA
                issues.append(f"invalid candidate enum {field}={cand.get(field)!r}")

    returned_phase = envelope.get("session_phase")
    if not returned_phase or is_placeholder(returned_phase):
        phase_val = PHASE_MISSING
    elif package_session_phase and str(returned_phase) != str(package_session_phase):
        phase_val = PHASE_MISMATCH
        issues.append(
            f"session_phase {returned_phase} != package {package_session_phase}"
        )
        if status == PARSE_VALID:
            status = PARSE_NEEDS_REVIEW
    else:
        phase_val = PHASE_MATCH

    live_ok = True
    claimed_live = envelope.get("live_session_evidence_available")
    pkg_phase = package_session_phase or ""
    if claimed_live is True and (
        pkg_phase in STALE_EVIDENCE_PHASES
        or package_live_session_evidence_available is False
    ):
        live_ok = False
        issues.append("result claims live_session_evidence_available while package evidence is not live")
        if status == PARSE_VALID:
            status = PARSE_NEEDS_REVIEW

    live_state_valid = (
        status == PARSE_VALID
        and phase_val != PHASE_MISMATCH
        and live_ok
        and analysis_type_ok
    )
    return {
        "structured_parse_status": status,
        "session_phase_validation": phase_val,
        "live_state_analysis_valid": live_state_valid,
        "issues": issues,
        "analysis_type_ok": analysis_type_ok,
        "returned_analysis_type": returned_type,
        "returned_session_phase": returned_phase,
        "package_session_phase": package_session_phase,
    }
