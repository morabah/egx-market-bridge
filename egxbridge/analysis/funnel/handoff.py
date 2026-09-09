from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import shutil

from egxbridge import __version__ as BRIDGE_VERSION
from egxbridge.analysis import WORKFLOW_VERSION
from egxbridge.analysis.common.ai_mode import AI_CHATGPT_HANDOFF, assert_handoff_only
from egxbridge.analysis.common.models import HandoffManifest, utc_now
from egxbridge.analysis.common.data_stamp import (
    build_data_stamp,
    copy_zip_sidecar,
    dated_zip_name,
    stamp_markdown,
    write_package_stamp,
    write_zip_sidecar,
)
from egxbridge.analysis.common.packaging import write_json, write_text, zip_directory, finalize_manifest, copy_file
from egxbridge.analysis.common.provenance import bridge_market_evidence, write_market_bundle
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.funnel.models import FunnelProject, CRITICAL_KEYS
from egxbridge.analysis.funnel.completion import sync_completion_fields
from egxbridge.analysis.funnel.state import (
    workspace_dir, ensure_workspace, save_project, load_project,
)


HERE = Path(__file__).resolve().parents[3]


def _funnel_request_md(project: FunnelProject, *, stage: str | None, evidence: dict[str, Any],
                       previous_status: str, mode: str) -> str:
    operation = getattr(project, "current_operation", None) or (
        "DELTA" if mode == "DELTA_ONLY" else mode
    )
    lines = [
        "# FUNNEL REQUEST — ChatGPT Handoff",
        "",
        f"- TICKER: **{project.ticker}**",
        f"- RUN MODE: **{mode}**",
        f"- CURRENT OPERATION: **{operation}**",
        f"- ANALYSIS OBJECTIVE: **{project.analysis_objective}**",
        f"- OWNERSHIP STATE: **{project.ownership_state}**",
        f"- HORIZON: **{project.intended_horizon or 'N/A'}**",
        f"- REQUIRED RETURN: **{project.personal_required_return or 'N/A'}**",
        f"- CAPITAL: **{project.proposed_capital or 'N/A'}**",
        f"- BENCHMARK: **{project.primary_benchmark}**",
        f"- CURRENT STAGE (underlying Funnel state): **{project.current_stage}**",
        f"- CLAIMED COMPLETED STAGES (metadata only): {', '.join(getattr(project, 'claimed_completed_stages', None) or project.completed_stages) or 'none'}",
        f"- VERIFIED COMPLETED STAGES: {', '.join(project.verified_completed_stages) or 'none'}",
        f"- SKIPPED STAGES (explicit): {', '.join(getattr(project, 'skipped_stages', None) or []) or 'none'}",
        f"- FUNNEL COMPLETION STATUS: **{project.funnel_completion_status}**",
        f"- COMPLETION BASIS: **{getattr(project, 'completion_basis', 'NONE')}**",
        f"- DELTA ELIGIBLE: **{project.delta_eligible}**",
        f"- LATEST COMPLETED MARKET SESSION: **{evidence.get('latest_completed_market_session') or 'N/A'}**",
        f"- SESSION DATE: **{evidence.get('session_date') or 'N/A'}**",
        f"- DATA CAPTURE CUTOFF: **{project.last_data_cutoff or 'see market_snapshot'}**",
        f"- PACKAGE GENERATED AT: **see DATA_STAMP.md (Cairo + UTC, distinct from session_date)**",
        f"- MARKET DATA QUALITY (research score): **{evidence.get('research_data_quality_score')}**",
        f"- MARKET DATA QUALITY (research grade): **{evidence.get('research_data_quality_grade')}**",
        f"- EXECUTION GRADE: **{evidence.get('execution_grade')}**",
        f"- EXECUTION DATA QUALITY (score): **{evidence.get('execution_data_quality_score')}**",
        f"- EXECUTION DATA QUALITY (grade): **{evidence.get('execution_data_quality_grade')}**",
        f"- VALUATION STATUS: **{project.valuation_status}**",
        f"- PREVIOUS FUNNEL STATUS: **{previous_status}**",
        f"- FUNNEL VERSION: **{project.funnel_version}**",
        f"- BRIDGE VERSION: **{BRIDGE_VERSION}**",
        f"- AI MODE: **{AI_CHATGPT_HANDOFF}**",
        "",
        "## Critical separation",
        "",
        "- EXECUTION_GRADE=NO does **not** block long-term valuation.",
        "- Do **not** let momentum/RVOL/breakouts redefine Fair Value or Sustainable Earnings.",
        "- Do **not** invent bid/ask, depth, trades, absorption, or Level-2 conclusions.",
        "- Missing fundamentals/news: research per Funnel rules; mark UNAVAILABLE when unknown.",
        "- funnel_completion_status and valuation_status are separate concepts.",
        "- claimed_completed_stages metadata alone never establishes COMPLETE.",
        "- current_operation is distinct from underlying current_stage.",
        "",
        "## Instruction",
        "",
        "Execute the attached master Funnel prompt **exactly** according to its own rules.",
        "Use funnel_result_schema.json for an optional structured partial or full result. Echo canonical_signal_id from forward_signal_context.json and declare research cutoff.",
        "Price-Implied Expectations, Expectations Gap, Revision Outlook, Fair Value, Fresh Capital Test and Final Decision are LLM-owned judgments; the app does not prefill or calculate them.",
        f"RUN MODE = {mode}",
        f"CURRENT OPERATION = {operation}",
        "",
        "Preserve previously established numbers unless new material evidence requires a correction",
        "with OLD VALUE / NEW VALUE / REASON / AFFECTED DOWNSTREAM STAGES.",
        "",
    ]
    if mode == "INTERACTIVE_STAGE_BY_STAGE":
        lines += [
            f"Complete **only** stage `{stage}`.",
            "Return a clear stage result the user can import back into EGX Market Bridge.",
            "",
        ]
    elif mode == "FULL_AUTOMATED_RUN":
        lines += [
            "Execute **all** Funnel stages in this conversation.",
            "Produce a complete Funnel result suitable for import.",
            "Tag the result with analysis_scope=FULL_FUNNEL, run_mode=FULL_AUTOMATED_RUN,",
            "result_type=COMPLETE_FUNNEL_RESULT.",
            "",
        ]
    elif mode == "DELTA_ONLY":
        lines += [
            "CURRENT OPERATION = DELTA",
            "This is a **DELTA** update (underlying Funnel stage state is unchanged).",
            "Identify new material evidence only; preserve previous critical numbers;",
            "recalculate only downstream dependencies.",
            "",
        ]
    return "\n".join(lines)


def prepare_funnel_handoff(
    project: FunnelProject,
    *,
    db=None,
    store: AnalysisStore | None = None,
    workspace_root: Path | None = None,
    output_root: Path | None = None,
    run_mode: str | None = None,
    stage: str | None = None,
    key_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build ChatGPT Funnel handoff package + ZIP. Never calls a paid LLM API."""
    assert_handoff_only()
    mode = run_mode or project.run_mode
    if mode == "DELTA_ONLY":
        from egxbridge.analysis.funnel.completion import compute_delta_eligible, delta_gate_payload
        if compute_delta_eligible(project, store=store, workspace_root=workspace_root) != "YES":
            return delta_gate_payload(project)
    project.run_mode = mode
    # Operation is distinct from underlying Funnel stage state
    if mode == "DELTA_ONLY":
        project.current_operation = "DELTA"
        # Do NOT overwrite current_stage with "DELTA"
    elif mode == "FULL_AUTOMATED_RUN":
        project.current_operation = "FULL_AUTOMATED_RUN"
    else:
        project.current_operation = f"STAGE_{stage or project.current_stage}"
    sync_completion_fields(project, store=store, workspace_root=workspace_root)
    ensure_workspace(project.ticker, workspace_root, project.funnel_version)
    evidence = bridge_market_evidence(db, project.ticker)
    # Distinct clocks: capture cutoff ≠ market session
    project.last_data_cutoff = utc_now()
    project.execution_grade_at_last_handoff = evidence.get("execution_grade")
    project.research_data_quality_at_last_handoff = evidence.get("research_data_quality_grade")
    project.research_data_quality_score_at_last_handoff = evidence.get("research_data_quality_score")
    project.execution_data_quality_score_at_last_handoff = evidence.get("execution_data_quality_score")
    blocked = False
    save_project(project, root=workspace_root, store=store)

    out_root = output_root or (HERE / "output" / "funnel_handoff")
    pkg = out_root / project.ticker
    if pkg.exists():
        shutil.rmtree(pkg)
    pkg.mkdir(parents=True)

    # Market evidence under market/ (README-consistent)
    write_market_bundle(pkg / "market", evidence)
    write_market_bundle(workspace_dir(project.ticker, workspace_root) / "market", evidence)

    short_version = project.funnel_version.rsplit("_v", 1)[-1]
    src_prompt = workspace_dir(project.ticker, workspace_root) / "source" / f"master_funnel_v{short_version}.md"
    copy_file(src_prompt, pkg / f"MASTER_FUNNEL_v{short_version}.md")
    from egxbridge.analysis.funnel.schema import result_schema
    write_json(pkg / "funnel_result_schema.json", result_schema())

    write_json(pkg / "project_state.json", project.to_dict())
    write_json(pkg / "historical_funnel_context.json", project.previous_funnel_context)
    linked = []
    if store:
        linked = [r for r in store.validation_records("forward_signal_snapshots") if r["ticker"] == project.ticker]
    write_json(pkg / "forward_signal_context.json", {
        "signals": linked, "instruction": "Copy the applicable canonical_signal_id into your result; never invent identity. Declare research and market-data cutoffs. Prior classifications are imported LLM context only.",
    })

    kv = key_values if key_values is not None else (store.all_key_values(project.ticker) if store else {})
    # Stage -1-only / partial is not a reliable previous Funnel for delta labeling
    if project.funnel_completion_status == "COMPLETE":
        prev_status = "EXISTS_COMPLETE"
    elif project.completed_stages or kv:
        prev_status = "EXISTS_PARTIAL"
    else:
        prev_status = "NOT_FOUND"

    write_json(pkg / "previous_funnel_summary.json", {
        "ticker": project.ticker,
        "previous_analysis_status": prev_status,
        "funnel_completion_status": project.funnel_completion_status,
        "delta_eligible": project.delta_eligible,
        "completion_basis": getattr(project, "completion_basis", "NONE"),
        "claimed_completed_stages": list(getattr(project, "claimed_completed_stages", None) or project.completed_stages or []),
        "completed_stages": project.completed_stages,
        "verified_completed_stages": list(project.verified_completed_stages or []),
        "skipped_stages": list(getattr(project, "skipped_stages", None) or []),
        "critical_values": {k: kv.get(k) for k in CRITICAL_KEYS},
        "imported_llm_structured_fields": project.structured_fields,
        "imported_llm_provenance": project.structured_provenance,
        "valuation_status": project.valuation_status,
        "last_valuation_date": project.last_valuation_date,
        "current_stage": project.current_stage,
        "current_operation": getattr(project, "current_operation", "STAGE"),
        "latest_completed_market_session": evidence.get("latest_completed_market_session"),
        "session_date": evidence.get("session_date"),
        "note": "Bridge does not fabricate Fair Value; values only if previously imported. "
                "valuation_status is separate from funnel_completion_status. "
                "COMPLETE requires verified interactive stages or FULL_AUTOMATED tagged result — "
                "never claimed_completed_stages metadata alone.",
    })

    stages_dir = pkg / "previous_stage_results"
    stages_dir.mkdir(parents=True)
    if store:
        for row in store.list_stage_results(project.ticker):
            if project.run_started_at and row["imported_at"] < project.run_started_at:
                continue
            sid = str(row["stage_id"]).replace(".", "_")
            write_text(stages_dir / f"stage_{sid}.md", row["content_text"])
    else:
        ws_stages = workspace_dir(project.ticker, workspace_root) / "stages"
        if ws_stages.exists():
            for p in ws_stages.rglob("*"):
                if p.is_file() and p.suffix in {".md", ".txt", ".json"}:
                    copy_file(p, stages_dir / p.name)

    corr = []
    if store:
        corr = store.list_corrections(project.ticker)
    corr_path = workspace_dir(project.ticker, workspace_root) / "results" / "correction_log.json"
    if corr_path.exists():
        try:
            corr = json.loads(corr_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    write_json(pkg / "correction_log.json", corr)

    stage_for_req = stage if mode == "INTERACTIVE_STAGE_BY_STAGE" else project.current_stage
    if mode == "FULL_AUTOMATED_RUN":
        stage_for_req = "ALL"
    # DELTA_ONLY: keep underlying current_stage; operation carries DELTA
    if mode == "DELTA_ONLY":
        stage_for_req = project.current_stage

    package_generated_at = utc_now()
    from egxbridge.universe import _daily_stats
    daily_status = _daily_stats(db, project.ticker)
    data_stamp = build_data_stamp(
        packaged_at=package_generated_at,
        session_close_date=evidence.get("latest_completed_market_session") or evidence.get("session_date"),
        package_kind="FUNNEL_HANDOFF",
        daily_rows=[{"ticker": project.ticker, **daily_status, "daily_bars": daily_status["count"], "data_captured_at": daily_status["captured_at"]}],
        daily_provider=",".join(str(p) for p in (evidence.get("providers_used") or []) if p) or None,
    )
    write_package_stamp(pkg, data_stamp)

    write_text(pkg / "funnel_request.md", _funnel_request_md(
        project, stage=stage_for_req, evidence=evidence, previous_status=prev_status, mode=mode,
    ))
    write_text(pkg / "README.md", f"""# ChatGPT Funnel Handoff — {project.ticker}

AI MODE: CHATGPT_HANDOFF (no paid API).

1. Upload this folder/ZIP to ChatGPT.
2. Start with `funnel_request.md` + `MASTER_FUNNEL_v{short_version}.md`.
3. Use `market/*.csv` and `market/*.json` as Bridge evidence only.
4. Paste/import the result back into EGX Market Bridge.

Execution Grade = {evidence.get('execution_grade')} does not block long-term valuation.

{stamp_markdown(data_stamp)}
""")
    manifest = HandoffManifest(
        bridge_version=BRIDGE_VERSION,
        workflow_type="FULL_FUNNEL",
        workflow_version=WORKFLOW_VERSION,
        generated_at=package_generated_at,
        ticker=project.ticker,
        funnel_prompt_version=project.funnel_version,
        analysis_objective=project.analysis_objective,
        run_mode=mode,
        data_cutoff=project.last_data_cutoff,
        latest_session=evidence.get("latest_completed_market_session"),
        research_data_quality=evidence.get("research_data_quality_grade"),
        execution_grade=evidence.get("execution_grade"),
        missing_capabilities=list(evidence.get("missing_capabilities") or []),
        provider_summary={
            "providers_used": evidence.get("providers_used") or [],
            "session_date": evidence.get("session_date"),
            "latest_completed_market_session": evidence.get("latest_completed_market_session"),
            "research_data_quality_score": evidence.get("research_data_quality_score"),
            "execution_data_quality_score": evidence.get("execution_data_quality_score"),
            "funnel_completion_status": project.funnel_completion_status,
            "delta_eligible": project.delta_eligible,
            "valuation_status": project.valuation_status,
        },
        previous_analysis_status=prev_status,
        ai_mode=AI_CHATGPT_HANDOFF,
        notes=[
            "No OpenAI/Anthropic/Gemini API used.",
            "Funnel reasoning is performed by ChatGPT user session.",
            "EXECUTION_GRADE=NO does not block Funnel preparation.",
            f"blocked={blocked}",
            "package_generated_at and data_capture_cutoff are distinct from session_date",
            "See DATA_STAMP.md for Cairo/UTC package time and session close date",
        ],
    )
    finalize_manifest(manifest, pkg)

    zip_path = out_root / dated_zip_name(f"{project.ticker}_CHATGPT_FUNNEL_HANDOFF", data_stamp)
    zip_directory(pkg, zip_path, arc_root=f"{project.ticker}_CHATGPT_FUNNEL_HANDOFF")
    write_zip_sidecar(zip_path, data_stamp)

    ws_h = workspace_dir(project.ticker, workspace_root) / "handoffs"
    ws_h.mkdir(parents=True, exist_ok=True)
    shutil.copy2(zip_path, ws_h / zip_path.name)
    copy_zip_sidecar(zip_path, ws_h / zip_path.name)

    if store:
        store._conn.execute(
            """INSERT INTO funnel_runs(ticker, run_mode, funnel_version, bridge_version, started_at, finished_at, status, manifest_json)
               VALUES (?,?,?,?,?,?,?,?)""",
            (project.ticker, mode, project.funnel_version, BRIDGE_VERSION, utc_now(), utc_now(),
             "HANDOFF_PREPARED", json.dumps(manifest.to_dict())),
        )
        store._conn.commit()

    return {
        "package_dir": str(pkg),
        "zip_path": str(zip_path),
        "manifest": manifest.to_dict(),
        "execution_grade": evidence.get("execution_grade"),
        "blocked_by_execution_grade": blocked,
        "ai_mode": AI_CHATGPT_HANDOFF,
        "session_date": evidence.get("session_date"),
        "latest_completed_market_session": evidence.get("latest_completed_market_session"),
        "funnel_completion_status": project.funnel_completion_status,
        "delta_eligible": project.delta_eligible,
        "valuation_status": project.valuation_status,
        "research_data_quality_score": evidence.get("research_data_quality_score"),
        "execution_data_quality_score": evidence.get("execution_data_quality_score"),
    }
