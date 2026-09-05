from __future__ import annotations

from pathlib import Path
from typing import Any

from egxbridge.analysis.funnel.models import FunnelProject
from egxbridge.analysis.funnel.handoff import prepare_funnel_handoff
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.funnel.models import CRITICAL_KEYS
from egxbridge.analysis.funnel.completion import (
    compute_delta_eligible,
    sync_completion_fields,
    delta_gate_payload,
    DELTA_ELIGIBLE_YES,
)
from egxbridge.analysis.funnel.state import save_project


def prepare_delta_handoff(
    project: FunnelProject,
    *,
    db=None,
    store: AnalysisStore | None = None,
    workspace_root: Path | None = None,
    output_root: Path | None = None,
) -> dict[str, Any]:
    """DELTA_ONLY — requires real imported Stage 11 baseline; no invented run modes."""
    sync_completion_fields(project, store=store, workspace_root=workspace_root)
    save_project(project, root=workspace_root, store=store)

    if compute_delta_eligible(project, store=store, workspace_root=workspace_root) != DELTA_ELIGIBLE_YES:
        return delta_gate_payload(project)

    kv = store.all_key_values(project.ticker) if store else {}
    critical = {k: kv.get(k) for k in CRITICAL_KEYS}
    project.run_mode = "DELTA_ONLY"
    result = prepare_funnel_handoff(
        project,
        db=db,
        store=store,
        workspace_root=workspace_root,
        output_root=output_root,
        run_mode="DELTA_ONLY",
        key_values=critical,
    )
    result["previous_critical_values"] = critical
    result["delta"] = True
    result["funnel_completion_status"] = project.funnel_completion_status
    result["delta_eligible"] = project.delta_eligible
    result["verified_completed_stages"] = list(project.verified_completed_stages or [])
    result["status"] = "OK"
    return result
