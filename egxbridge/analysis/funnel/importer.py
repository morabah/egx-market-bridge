from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re

from egxbridge import __version__ as BRIDGE_VERSION
from egxbridge.analysis.common.models import utc_now, content_hash, AnalysisProvenance
from egxbridge.analysis.common.packaging import write_json, write_text
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.funnel.models import CRITICAL_KEYS
from egxbridge.analysis.funnel.state import workspace_dir, load_project, mark_stage_complete, save_project
from egxbridge.analysis.funnel.completion import (
    valuation_status_for_import,
    sync_completion_fields,
    extract_result_tags,
    is_complete_funnel_result,
    is_explicit_stage_skip,
    FULL_AUTOMATED_RESULT_ID,
)


def _optional_extract_keys(text: str) -> dict[str, str]:
    """Low-confidence optional extraction — never discard original text."""
    found: dict[str, str] = {}
    for key in CRITICAL_KEYS:
        # patterns like **Fair Value**: 12.3 or Fair Value = 12.3
        pat = rf"{re.escape(key)}\s*[:=]\s*([^\n\|]+)"
        m = re.search(pat, text, flags=re.I)
        if m:
            found[key] = m.group(1).strip()[:200]
    return found


def import_funnel_result(
    ticker: str,
    source: Path | str,
    *,
    stage_id: str | None = None,
    store: AnalysisStore | None = None,
    workspace_root: Path | None = None,
    run_mode: str | None = None,
    advance_stage: bool = True,
) -> dict[str, Any]:
    """Import ChatGPT Funnel result (.md/.txt/.json). Preserve original text unchanged."""
    from egxbridge.analysis.schedule.importer import read_source, extract_json_envelope
    from egxbridge.analysis.funnel.schema import extract_summary
    content, source_file = read_source(source)
    envelope = extract_json_envelope(content)

    ticker = ticker.upper()
    project = load_project(ticker, workspace_root)
    if project is None:
        raise FileNotFoundError(f"No Funnel project for {ticker}")

    declared_version = (envelope or {}).get("funnel_version")
    if declared_version and str(declared_version).rsplit("_v", 1)[-1] != project.funnel_version.rsplit("_v", 1)[-1]:
        rejected = workspace_dir(ticker, workspace_root) / "results" / f"rejected_import_{content_hash(content)[:12]}.md"
        write_text(rejected, content)
        raise ValueError("Imported Funnel version differs from this project; raw result preserved outside verified stage files")
    stage = stage_id or project.current_stage
    h = content_hash(content)
    tags = extract_result_tags(content)
    # FULL_AUTOMATED complete result stored under dedicated id (no separate stage files required)
    if is_complete_funnel_result(content) or (
        (run_mode or project.run_mode) == "FULL_AUTOMATED_RUN"
        and is_complete_funnel_result(content, {"run_mode": "FULL_AUTOMATED_RUN", **tags})
    ):
        stage = FULL_AUTOMATED_RESULT_ID
    base = workspace_dir(ticker, workspace_root)
    stage_dir = base / "stages" / f"stage_{str(stage).replace('.', '_')}"
    stage_dir.mkdir(parents=True, exist_ok=True)
    out_file = stage_dir / f"result_{h[:12]}.md"
    write_text(out_file, content)  # original unchanged
    write_text(base / "results" / "latest_funnel_result.md", content)

    extracted = _optional_extract_keys(content)
    fields, schema_issues = extract_summary(content, envelope)
    imported_at = utc_now()
    source_cutoff = (envelope or {}).get("declared_research_cutoff") or (envelope or {}).get("source_cutoff")
    provenance = {"classification_source": "FUNNEL_LLM", "analysis_imported_at": imported_at,
                  "analysis_started_at": (envelope or {}).get("analysis_started_at"),
                  "source_cutoff": source_cutoff, "market_data_cutoff": (envelope or {}).get("market_data_cutoff"),
                  "funnel_version": project.funnel_version, "content_hash": h,
                  "decision_kind": "IMPORTED_LLM_DECISION"}
    previous_provenance = project.structured_provenance
    field_provenance = dict(previous_provenance.get("field_provenance") or {
        key: previous_provenance for key in project.structured_fields
    })
    field_provenance.update({key: provenance for key in fields})
    project.structured_fields.update(fields)
    project.structured_provenance = {**provenance, "field_provenance": field_provenance}
    classification_linkage = "NO_CANONICAL_SIGNAL_SUPPLIED"
    cid = (envelope or {}).get("canonical_signal_id")
    if store and cid:
        from egxbridge.analysis.forward_validation import append_classification
        try:
            append_classification(store, cid, ticker=ticker, fields=fields, source="FUNNEL_LLM", source_id=h,
                source_cutoff=source_cutoff, funnel_version=project.funnel_version,
                analysis_started_at=provenance["analysis_started_at"], market_data_cutoff=provenance["market_data_cutoff"])
            classification_linkage = "LINKED"
        except ValueError as exc:
            classification_linkage = "INVALID_CANONICAL_IDENTITY"
            schema_issues.append(str(exc))
    meta = {
        "extracted_keys_optional": extracted,
        "structured_fields": fields, "structured_provenance": provenance, "schema_issues": schema_issues,
        "funnel_version": project.funnel_version, "run_started_at": project.run_started_at,
        "extraction_confidence": "LOW" if extracted else "NONE",
        **{k: tags[k] for k in ("analysis_scope", "run_mode", "result_type") if k in tags},
    }
    if is_explicit_stage_skip(content, meta):
        meta["skipped"] = True
        meta["skip_reason"] = tags.get("skip_reason") or "explicit STAGE_SKIPPED"
    if stage == FULL_AUTOMATED_RESULT_ID:
        meta["analysis_scope"] = meta.get("analysis_scope") or "FULL_FUNNEL"
        meta["run_mode"] = meta.get("run_mode") or "FULL_AUTOMATED_RUN"
        meta["result_type"] = meta.get("result_type") or "COMPLETE_FUNNEL_RESULT"

    if store:
        store.insert_stage_result(ticker, str(stage), content, source_file=source_file, meta=meta)
        for k, v in extracted.items():
            store.set_key_value(
                ticker, k, v,
                as_of=utc_now(),
                source_stage=str(stage),
                reason="optional extraction from imported Funnel text",
                source=source_file,
            )
        prov = AnalysisProvenance(
            analysis_type="FULL_FUNNEL",
            ticker_or_universe=ticker,
            generated_at=utc_now(),
            imported_at=utc_now(),
            funnel_version=project.funnel_version,
            bridge_version=BRIDGE_VERSION,
            data_cutoff=project.last_data_cutoff,
            source_file=source_file,
            content_hash=h,
            run_mode=run_mode or project.run_mode,
        )
        store.record_import(prov.to_dict(), content)

    # Append valuation history if Fair Value present
    hist_path = base / "results" / "valuation_history.json"
    hist = []
    if hist_path.exists():
        try:
            hist = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception:
            hist = []
    if "Fair Value" in extracted or "Blended Fair Value" in extracted:
        hist.append({
            "recorded_at": utc_now(),
            "fair_value": extracted.get("Fair Value") or extracted.get("Blended Fair Value"),
            "stage": stage,
            "content_hash": h,
        })
        if extracted.get("Valuation date"):
            project.last_valuation_date = extracted["Valuation date"]
        project.valuation_status = valuation_status_for_import(
            fair_value=extracted.get("Fair Value") or extracted.get("Blended Fair Value"),
            valuation_date=project.last_valuation_date or extracted.get("Valuation date"),
            current=project.valuation_status,
        )
    elif project.last_valuation_date is None and project.valuation_status == "UPDATED":
        project.valuation_status = "NOT_ESTABLISHED"
    write_json(hist_path, hist)

    sync_completion_fields(project, store=store, workspace_root=workspace_root)

    summary = {
        "ticker": ticker,
        "last_imported_stage": stage,
        "imported_at": utc_now(),
        "content_hash": h,
        "optional_extracted_keys": extracted,
        "structured_fields": fields, "schema_issues": schema_issues, "classification_linkage": classification_linkage,
        "completed_stages": list(project.completed_stages),
        "funnel_completion_status": project.funnel_completion_status,
        "delta_eligible": project.delta_eligible,
        "completion_basis": project.completion_basis,
        "valuation_status": project.valuation_status,
    }
    write_json(base / "results" / "current_summary.json", summary)

    if advance_stage and stage != FULL_AUTOMATED_RESULT_ID:
        mark_stage_complete(project, str(stage), root=workspace_root, store=store)
    else:
        if stage == FULL_AUTOMATED_RESULT_ID:
            # Do not invent completed_stages metadata for full-run; verification uses tagged result
            project.run_mode = "FULL_AUTOMATED_RUN"
            sync_completion_fields(project, store=store, workspace_root=workspace_root)
        save_project(project, root=workspace_root, store=store)

    # sync correction log file from store
    if store:
        write_json(base / "results" / "correction_log.json", store.list_corrections(ticker))

    return {
        "ticker": ticker,
        "stage_id": stage,
        "content_hash": h,
        "saved_path": str(out_file),
        "original_preserved": True,
        "optional_extracted_keys": extracted,
        "structured_fields": fields, "schema_issues": schema_issues, "classification_linkage": classification_linkage,
        "project": load_project(ticker, workspace_root).to_dict() if load_project(ticker, workspace_root) else None,
    }
