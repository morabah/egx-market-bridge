from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import shutil

from egxbridge.analysis import FUNNEL_PROMPT_VERSION
from egxbridge.analysis.funnel.models import FunnelProject, FUNNEL_STAGES
from egxbridge.analysis.common.models import utc_now
from egxbridge.analysis.common.packaging import write_json, write_text, copy_file
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.common.environment import PRODUCTION, normalize_environment


HERE = Path(__file__).resolve().parents[3]  # repo root
DEFAULT_WORKSPACE = HERE / "workspace" / "funnels"
PROMPT_PATH = HERE / "EGX_STOCK_ANALYSIS_FUNNEL_v2.8.md"


def prompt_path(version: str) -> Path:
    short = version.rsplit("_v", 1)[-1]
    if short not in {"2.7", "2.8"}:
        raise ValueError(f"Unsupported Funnel version: {version}")
    return PROMPT_PATH if short == "2.8" else HERE / "prompts" / "EGX_STOCK_ANALYSIS_FUNNEL_v2.7.md"


def workspace_dir(ticker: str, root: Path | None = None) -> Path:
    return (root or DEFAULT_WORKSPACE) / ticker.upper()


def ensure_workspace(ticker: str, root: Path | None = None, version: str = FUNNEL_PROMPT_VERSION) -> Path:
    base = workspace_dir(ticker, root)
    for sub in ("source", "market", "stages", "results", "handoffs"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    for stage in FUNNEL_STAGES:
        (base / "stages" / f"stage_{stage.replace('.', '_')}").mkdir(parents=True, exist_ok=True)
    # Preserve authoritative prompt
    source = prompt_path(version)
    target = base / "source" / f"master_funnel_v{version.rsplit('_v', 1)[-1]}.md"
    if not target.exists():
        copy_file(source, target)
    return base


def save_project(project: FunnelProject, root: Path | None = None, store: AnalysisStore | None = None) -> Path:
    base = ensure_workspace(project.ticker, root, project.funnel_version)
    project.updated_at = utc_now()
    write_json(base / "project.json", project.to_dict())
    write_json(base / "funnel_state.json", {
        "current_stage": project.current_stage,
        "current_operation": getattr(project, "current_operation", "STAGE"),
        "completed_stages": project.completed_stages,
        "claimed_completed_stages": getattr(project, "claimed_completed_stages", project.completed_stages),
        "verified_completed_stages": getattr(project, "verified_completed_stages", []),
        "skipped_stages": getattr(project, "skipped_stages", []),
        "funnel_completion_status": getattr(project, "funnel_completion_status", "NOT_STARTED"),
        "completion_basis": getattr(project, "completion_basis", "NONE"),
        "delta_eligible": getattr(project, "delta_eligible", "NO"),
        "valuation_status": project.valuation_status,
        "last_data_cutoff": project.last_data_cutoff,
        "last_news_cutoff": project.last_news_cutoff,
        "last_valuation_date": project.last_valuation_date,
        "funnel_version": project.funnel_version,
        "run_started_at": project.run_started_at,
        "archived_funnel_workspace": project.archived_funnel_workspace,
        "structured_fields": project.structured_fields,
        "structured_provenance": project.structured_provenance,
        "updated_at": project.updated_at,
    })
    if store:
        store.upsert_project(project.ticker, "funnel", project.to_dict())
    return base


def load_project(ticker: str, root: Path | None = None) -> FunnelProject | None:
    path = workspace_dir(ticker, root) / "project.json"
    if not path.exists():
        return None
    return FunnelProject.from_dict(json.loads(path.read_text(encoding="utf-8")))


def create_project(
    ticker: str,
    *,
    analysis_objective: str = "FULL_HYBRID_REVIEW",
    ownership_state: str = "NOT_OWNED",
    run_mode: str = "INTERACTIVE_STAGE_BY_STAGE",
    intended_horizon: str = "",
    personal_required_return: str = "",
    proposed_capital: str = "",
    primary_benchmark: str = "EGX30",
    company_name_if_known: str = "",
    root: Path | None = None,
    store: AnalysisStore | None = None,
    environment: str | None = None,
) -> FunnelProject:
    existing = load_project(ticker, root)
    if existing:
        return existing
    env = normalize_environment(
        environment
        or getattr(store, "environment", None)
        or PRODUCTION
    )
    project = FunnelProject(
        ticker=ticker,
        company_name_if_known=company_name_if_known,
        funnel_version=FUNNEL_PROMPT_VERSION,
        analysis_objective=analysis_objective,
        ownership_state=ownership_state,
        run_mode=run_mode,
        intended_horizon=intended_horizon,
        personal_required_return=personal_required_return,
        proposed_capital=proposed_capital,
        primary_benchmark=primary_benchmark,
        current_stage="-1",
        completed_stages=[],
        valuation_status="NOT_STARTED",
        environment=env,
    )
    save_project(project, root=root, store=store)
    # init result files
    base = workspace_dir(ticker, root)
    write_json(base / "results" / "correction_log.json", [])
    write_json(base / "results" / "valuation_history.json", [])
    write_json(base / "results" / "current_summary.json", {"ticker": ticker.upper(), "status": "NOT_STARTED"})
    return project


def next_stage(current: str) -> str | None:
    try:
        i = FUNNEL_STAGES.index(current)
    except ValueError:
        return FUNNEL_STAGES[0]
    if i + 1 >= len(FUNNEL_STAGES):
        return None
    return FUNNEL_STAGES[i + 1]


def mark_stage_complete(project: FunnelProject, stage_id: str, root: Path | None = None,
                        store: AnalysisStore | None = None) -> FunnelProject:
    from egxbridge.analysis.funnel.completion import sync_completion_fields

    if stage_id not in project.completed_stages:
        project.completed_stages.append(stage_id)
    nxt = next_stage(stage_id)
    if nxt == "9.5" and project.funnel_version.endswith("2.7"):
        nxt = "10"
    if nxt:
        project.current_stage = nxt
    # Do NOT conflate funnel completion with valuation_status; completion is import-verified
    sync_completion_fields(project, store=store, workspace_root=root)
    project.updated_at = utc_now()
    save_project(project, root=root, store=store)
    return project


def start_current_full_run(project: FunnelProject, *, root: Path | None = None, store=None) -> FunnelProject:
    """A new full run uses the current prompt. Continuation/delta retain their baseline version."""
    if project.funnel_version.rsplit("_v", 1)[-1] == FUNNEL_PROMPT_VERSION:
        return project
    started = utc_now()
    base = workspace_dir(project.ticker, root)
    archive = (root or DEFAULT_WORKSPACE) / "_history" / project.ticker / started.replace(":", "-")
    archive.parent.mkdir(parents=True, exist_ok=True)
    base.rename(archive)  # Retain exact old project, prompts, stage files and handoff files.
    mandate = {k: getattr(project, k) for k in (
        "analysis_objective", "ownership_state", "intended_horizon", "personal_required_return",
        "proposed_capital", "primary_benchmark", "company_name_if_known")}
    current = create_project(project.ticker, root=root, store=store, environment=project.environment,
                             run_mode="FULL_AUTOMATED_RUN", **mandate)
    current.run_started_at = started
    current.archived_funnel_workspace = str(archive)
    current.previous_funnel_context = project.to_dict()
    save_project(current, root=root, store=store)
    return current
