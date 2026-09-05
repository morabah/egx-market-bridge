"""Import-verified Funnel completion and DELTA eligibility (v0.4.3)."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import re

from egxbridge.analysis.funnel.models import FunnelProject, FUNNEL_STAGES


FUNNEL_COMPLETION_NOT_STARTED = "NOT_STARTED"
FUNNEL_COMPLETION_PARTIAL = "PARTIAL"
FUNNEL_COMPLETION_COMPLETE = "COMPLETE"

DELTA_ELIGIBLE_YES = "YES"
DELTA_ELIGIBLE_NO = "NO"

COMPLETION_BASIS_INTERACTIVE = "INTERACTIVE_VERIFIED"
COMPLETION_BASIS_FULL_AUTOMATED = "FULL_AUTOMATED_VERIFIED"
COMPLETION_BASIS_PARTIAL = "PARTIAL"
COMPLETION_BASIS_NONE = "NONE"

DELTA_BASELINE_STAGE = "11"
FULL_AUTOMATED_RESULT_ID = "FULL_AUTOMATED"

# Interactive COMPLETE requires verified (or explicitly skipped) stages through 11.
REQUIRED_INTERACTIVE_STAGES = list(FUNNEL_STAGES)

_STAGE11_VALUATION_MARKERS = re.compile(
    r"(valuation\s*status|fair\s*value|not[_\s-]?reliable|not[_\s-]?established|"
    r"final\s*decision|blended\s*fair\s*value)",
    re.I,
)

_TAG_PATTERNS = {
    "analysis_scope": re.compile(r"analysis_scope\s*[:=]\s*(\S+)", re.I),
    "run_mode": re.compile(r"run_mode\s*[:=]\s*(\S+)", re.I),
    "result_type": re.compile(r"result_type\s*[:=]\s*(\S+)", re.I),
}

PLACEHOLDER_FV = re.compile(
    r"^(placeholder(_pending)?|pending(_research)?|tbd|n/?a|none|null)?$",
    re.I,
)

_PLACEHOLDER_STAGE_CONTENT = re.compile(
    r"(placeholder|synthetic\s+stub|TODO_STAGE|STAGE_STUB_ONLY)",
    re.I,
)


def is_placeholder_fair_value(value: Any) -> bool:
    if value is None:
        return True
    s = str(value).strip()
    if not s:
        return True
    if PLACEHOLDER_FV.match(s):
        return True
    if "placeholder" in s.lower() or s.upper() == "PLACEHOLDER_PENDING":
        return True
    return False


def sanitize_fair_value(value: Any) -> Any:
    return None if is_placeholder_fair_value(value) else value


def extract_result_tags(content: str, meta: dict | None = None) -> dict[str, str]:
    tags: dict[str, str] = {}
    if meta:
        for k in ("analysis_scope", "run_mode", "result_type", "skipped", "skip_reason"):
            if meta.get(k) is not None:
                tags[k] = str(meta[k])
    text = content or ""
    for key, pat in _TAG_PATTERNS.items():
        if key not in tags:
            m = pat.search(text)
            if m:
                tags[key] = m.group(1).strip().strip("\"'`")
    return tags


def is_complete_funnel_result(content: str, meta: dict | None = None) -> bool:
    tags = extract_result_tags(content, meta)
    return (
        tags.get("analysis_scope") == "FULL_FUNNEL"
        and tags.get("run_mode") == "FULL_AUTOMATED_RUN"
        and tags.get("result_type") == "COMPLETE_FUNNEL_RESULT"
    )


def is_explicit_stage_skip(content: str, meta: dict | None = None) -> bool:
    tags = extract_result_tags(content, meta)
    if str(tags.get("skipped", "")).lower() in {"1", "true", "yes"}:
        return True
    head = (content or "").lstrip()[:80].upper()
    return head.startswith("STAGE_SKIPPED") or "STAGE_SKIPPED:" in (content or "").upper()


def _workspace_stage_files(ticker: str, stage_id: str, workspace_root: Path | None) -> list[Path]:
    if workspace_root is None:
        return []
    stage_dir = workspace_root / ticker.upper() / "stages" / f"stage_{str(stage_id).replace('.', '_')}"
    if not stage_dir.exists():
        return []
    return [p for p in stage_dir.iterdir() if p.is_file() and p.suffix in {".md", ".txt", ".json"}]


def verify_imported_stage(
    ticker: str,
    stage_id: str,
    *,
    store=None,
    workspace_root: Path | None = None,
) -> dict[str, Any] | None:
    """Verified only when persisted import has stage_id, content, import_timestamp, content_hash."""
    ticker = ticker.upper()
    stage_id = str(stage_id)
    row = store.get_stage_result(ticker, stage_id) if store is not None else None
    from egxbridge.analysis.funnel.state import load_project
    project = load_project(ticker, workspace_root)
    if row and project and project.run_started_at and (row.get("imported_at") or "") < project.run_started_at:
        row = None
    files = _workspace_stage_files(ticker, stage_id, workspace_root)

    content = ""
    content_hash = None
    imported_at = None
    source_file = None
    meta: dict = {}
    if row:
        content = row.get("content_text") or ""
        content_hash = row.get("content_hash")
        imported_at = row.get("imported_at")
        source_file = row.get("source_file")
        meta = row.get("meta") or {}
    elif files:
        newest = max(files, key=lambda p: p.stat().st_mtime)
        content = newest.read_text(encoding="utf-8")
        from egxbridge.analysis.common.models import content_hash as ch
        content_hash = ch(content)
        source_file = str(newest)

    if not content or not str(content).strip() or not content_hash:
        return None

    skipped = is_explicit_stage_skip(content, meta)
    tags = extract_result_tags(content, meta)

    evidence = {
        "stage_id": stage_id,
        "content_hash": content_hash,
        "imported_at": imported_at,
        "source_file": source_file,
        "content_len": len(content),
        "store_backed": bool(row),
        "workspace_files": [str(p) for p in files],
        "skipped": skipped,
        "tags": tags,
        "valid": False,
    }

    # Must be store-backed with import timestamp to count as verified
    if not (row and imported_at and content_hash and content.strip()):
        return evidence

    if skipped:
        # Stage 11 cannot be skipped for a COMPLETE baseline
        evidence["valid"] = stage_id != DELTA_BASELINE_STAGE
        evidence["satisfaction"] = "SKIPPED" if evidence["valid"] else "INVALID_SKIP"
        return evidence

    if stage_id == DELTA_BASELINE_STAGE:
        if _PLACEHOLDER_STAGE_CONTENT.search(content):
            evidence["valid"] = False
            evidence["rejection"] = "PLACEHOLDER_STAGE11"
            return evidence
        if len(content.strip()) < 40:
            evidence["valid"] = False
            evidence["rejection"] = "TOO_SHORT"
            return evidence
        evidence["valuation_documented"] = bool(_STAGE11_VALUATION_MARKERS.search(content))
        evidence["valid"] = bool(evidence["valuation_documented"])
        evidence["satisfaction"] = "VERIFIED" if evidence["valid"] else "INVALID"
        return evidence

    if stage_id == FULL_AUTOMATED_RESULT_ID:
        evidence["valid"] = is_complete_funnel_result(content, meta)
        evidence["satisfaction"] = "FULL_AUTOMATED" if evidence["valid"] else "INVALID"
        return evidence

    evidence["valid"] = True
    evidence["satisfaction"] = "VERIFIED"
    return evidence


def list_verified_stages(
    ticker: str,
    *,
    store=None,
    workspace_root: Path | None = None,
    stage_ids: list[str] | None = None,
) -> list[str]:
    ids = stage_ids or REQUIRED_INTERACTIVE_STAGES
    out = []
    for sid in ids:
        ev = verify_imported_stage(ticker, sid, store=store, workspace_root=workspace_root)
        if ev and ev.get("valid") and not ev.get("skipped"):
            out.append(sid)
    return out


def list_verified_skips(
    ticker: str,
    *,
    store=None,
    workspace_root: Path | None = None,
) -> list[str]:
    out = []
    from egxbridge.analysis.funnel.state import load_project
    project = load_project(ticker, workspace_root)
    for sid in REQUIRED_INTERACTIVE_STAGES:
        if sid == "9.5" and project and project.funnel_version.endswith("2.7"):
            continue
        if sid == DELTA_BASELINE_STAGE:
            continue
        ev = verify_imported_stage(ticker, sid, store=store, workspace_root=workspace_root)
        if ev and ev.get("valid") and ev.get("skipped"):
            out.append(sid)
    return out


def verify_full_automated_result(
    ticker: str,
    *,
    store=None,
    workspace_root: Path | None = None,
) -> dict[str, Any] | None:
    ev = verify_imported_stage(
        ticker, FULL_AUTOMATED_RESULT_ID, store=store, workspace_root=workspace_root,
    )
    if ev and ev.get("valid"):
        return ev
    return None


def _interactive_required_satisfied(
    ticker: str,
    *,
    store=None,
    workspace_root: Path | None = None,
) -> tuple[bool, list[str], list[str], list[str]]:
    """Return (ok, verified, skipped, missing)."""
    verified: list[str] = []
    skipped: list[str] = []
    missing: list[str] = []
    from egxbridge.analysis.funnel.state import load_project
    project = load_project(ticker, workspace_root)
    for sid in REQUIRED_INTERACTIVE_STAGES:
        if sid == "9.5" and project and project.funnel_version.endswith("2.7"):
            continue
        ev = verify_imported_stage(ticker, sid, store=store, workspace_root=workspace_root)
        if ev and ev.get("valid") and ev.get("skipped"):
            skipped.append(sid)
        elif ev and ev.get("valid"):
            verified.append(sid)
        else:
            missing.append(sid)
    return (not missing, verified, skipped, missing)


def compute_completion_basis(
    project: FunnelProject | None,
    *,
    store=None,
    workspace_root: Path | None = None,
) -> str:
    if project is None:
        return COMPLETION_BASIS_NONE

    # B) FULL_AUTOMATED_RUN complete result
    full = verify_full_automated_result(
        project.ticker, store=store, workspace_root=workspace_root,
    )
    if full:
        return COMPLETION_BASIS_FULL_AUTOMATED

    # A) Interactive: all required stages verified or explicitly skipped
    ok, verified, skipped, missing = _interactive_required_satisfied(
        project.ticker, store=store, workspace_root=workspace_root,
    )
    if ok and DELTA_BASELINE_STAGE in verified:
        return COMPLETION_BASIS_INTERACTIVE

    if verified or skipped:
        return COMPLETION_BASIS_PARTIAL
    return COMPLETION_BASIS_NONE


def compute_funnel_completion_status(
    project: FunnelProject | None,
    *,
    store=None,
    workspace_root: Path | None = None,
) -> str:
    """COMPLETE never from claimed_completed_stages / completed_stages metadata alone."""
    if project is None:
        return FUNNEL_COMPLETION_NOT_STARTED
    basis = compute_completion_basis(project, store=store, workspace_root=workspace_root)
    if basis in {COMPLETION_BASIS_INTERACTIVE, COMPLETION_BASIS_FULL_AUTOMATED}:
        return FUNNEL_COMPLETION_COMPLETE
    if basis == COMPLETION_BASIS_PARTIAL:
        return FUNNEL_COMPLETION_PARTIAL
    return FUNNEL_COMPLETION_NOT_STARTED


def compute_delta_eligible(
    project: FunnelProject | None,
    *,
    store=None,
    workspace_root: Path | None = None,
) -> str:
    basis = compute_completion_basis(project, store=store, workspace_root=workspace_root)
    if basis in {COMPLETION_BASIS_INTERACTIVE, COMPLETION_BASIS_FULL_AUTOMATED}:
        return DELTA_ELIGIBLE_YES
    return DELTA_ELIGIBLE_NO


def sync_completion_fields(
    project: FunnelProject,
    *,
    store=None,
    workspace_root: Path | None = None,
) -> FunnelProject:
    # Claimed = metadata only (never establishes COMPLETE by itself)
    project.claimed_completed_stages = list(project.completed_stages or [])
    verified = list_verified_stages(
        project.ticker, store=store, workspace_root=workspace_root,
    )
    # Also surface FULL_AUTOMATED as verified marker when present
    full = verify_full_automated_result(
        project.ticker, store=store, workspace_root=workspace_root,
    )
    if full and FULL_AUTOMATED_RESULT_ID not in verified:
        verified = verified + [FULL_AUTOMATED_RESULT_ID]
    project.verified_completed_stages = verified
    project.skipped_stages = list_verified_skips(
        project.ticker, store=store, workspace_root=workspace_root,
    )
    project.completion_basis = compute_completion_basis(
        project, store=store, workspace_root=workspace_root,
    )
    project.funnel_completion_status = compute_funnel_completion_status(
        project, store=store, workspace_root=workspace_root,
    )
    project.delta_eligible = compute_delta_eligible(
        project, store=store, workspace_root=workspace_root,
    )

    # Hard reject invalid combo
    if project.funnel_completion_status == FUNNEL_COMPLETION_COMPLETE:
        if project.completion_basis not in {
            COMPLETION_BASIS_INTERACTIVE, COMPLETION_BASIS_FULL_AUTOMATED,
        }:
            project.funnel_completion_status = FUNNEL_COMPLETION_PARTIAL
            project.delta_eligible = DELTA_ELIGIBLE_NO
            project.completion_basis = COMPLETION_BASIS_PARTIAL
    if project.delta_eligible == DELTA_ELIGIBLE_YES and project.completion_basis not in {
        COMPLETION_BASIS_INTERACTIVE, COMPLETION_BASIS_FULL_AUTOMATED,
    }:
        project.delta_eligible = DELTA_ELIGIBLE_NO
    return project


def valuation_status_for_import(
    *,
    fair_value: str | None,
    valuation_date: str | None,
    current: str,
) -> str:
    fv = (fair_value or "").strip()
    vd = (valuation_date or "").strip()
    if is_placeholder_fair_value(fv) or fv.lower() in {
        "not established yet", "not set yet", "n/a", "none", "null", "not_reliable", "not reliable",
    }:
        if "not_reliable" in fv.lower() or "not reliable" in fv.lower():
            return "NOT_RELIABLE"
        if current in {"UPDATED", "COMPLETE", "CURRENT"}:
            return "NOT_ESTABLISHED"
        return current if current not in {"UPDATED"} else "NOT_ESTABLISHED"
    if not vd:
        return "NOT_ESTABLISHED"
    return "UPDATED"


def delta_gate_payload(project: FunnelProject) -> dict[str, Any]:
    return {
        "status": "DELTA_NOT_AVAILABLE",
        "reason": "REQUIRES_FULL_BUILD",
        "funnel_completion_status": project.funnel_completion_status,
        "delta_eligible": project.delta_eligible,
        "completion_basis": getattr(project, "completion_basis", COMPLETION_BASIS_NONE),
        "claimed_completed_stages": list(getattr(project, "claimed_completed_stages", None) or project.completed_stages or []),
        "verified_completed_stages": list(getattr(project, "verified_completed_stages", None) or []),
        "skipped_stages": list(getattr(project, "skipped_stages", None) or []),
        "message": (
            "DELTA_ONLY requires a verified COMPLETE baseline: either all required interactive "
            "stages through Stage 11 (verified imports / explicit skips), or a FULL_AUTOMATED_RUN "
            "result tagged analysis_scope=FULL_FUNNEL, result_type=COMPLETE_FUNNEL_RESULT. "
            "claimed_completed_stages metadata alone is never sufficient."
        ),
        "suggested_modes": ["FULL_AUTOMATED_RUN", "INTERACTIVE_STAGE_BY_STAGE"],
        "zip_path": None,
        "package_dir": None,
        "delta": False,
        "blocked": True,
    }
