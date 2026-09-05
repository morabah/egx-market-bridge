from __future__ import annotations

from pathlib import Path
from typing import Any

from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.common.environment import PRODUCTION, normalize_environment, workspace_root_for
from egxbridge.analysis.funnel.state import create_project, load_project, workspace_dir
from egxbridge.analysis.funnel.handoff import prepare_funnel_handoff
from egxbridge.analysis.funnel.importer import import_funnel_result
from egxbridge.analysis.funnel.delta import prepare_delta_handoff
from egxbridge.analysis.funnel.models import FunnelProject
from egxbridge.analysis.funnel.completion import (
    sync_completion_fields,
    sanitize_fair_value,
    FUNNEL_COMPLETION_COMPLETE,
    FUNNEL_COMPLETION_PARTIAL,
    FUNNEL_COMPLETION_NOT_STARTED,
    DELTA_ELIGIBLE_YES,
)


class FunnelRegistry:
    """Facade for Funnel workspace operations."""

    def __init__(
        self,
        workspace_root: Path | None = None,
        store: AnalysisStore | None = None,
        db=None,
        environment: str | None = None,
    ):
        if environment is None:
            environment = getattr(store, "environment", None) or PRODUCTION
        self.environment = normalize_environment(environment)
        self.workspace_root = Path(workspace_root) if workspace_root else workspace_root_for(self.environment)
        self.store = store
        self.db = db

    def create(self, ticker: str, **kwargs) -> FunnelProject:
        kwargs.setdefault("environment", self.environment)
        return create_project(ticker, root=self.workspace_root, store=self.store, **kwargs)

    def get(self, ticker: str) -> FunnelProject | None:
        return load_project(ticker, self.workspace_root)

    def prepare_stage(self, ticker: str, stage: str | None = None) -> dict[str, Any]:
        p = self.get(ticker) or self.create(ticker)
        p.run_mode = "INTERACTIVE_STAGE_BY_STAGE"
        return prepare_funnel_handoff(
            p, db=self.db, store=self.store, workspace_root=self.workspace_root,
            run_mode="INTERACTIVE_STAGE_BY_STAGE", stage=stage or p.current_stage,
        )

    def prepare_full(self, ticker: str) -> dict[str, Any]:
        p = self.get(ticker) or self.create(ticker)
        from egxbridge.analysis.funnel.state import start_current_full_run
        p = start_current_full_run(p, root=self.workspace_root, store=self.store)
        return prepare_funnel_handoff(
            p, db=self.db, store=self.store, workspace_root=self.workspace_root,
            run_mode="FULL_AUTOMATED_RUN",
        )

    def prepare_delta(self, ticker: str) -> dict[str, Any]:
        p = self.get(ticker) or self.create(ticker)
        return prepare_delta_handoff(p, db=self.db, store=self.store, workspace_root=self.workspace_root)

    def import_result(self, ticker: str, source: str | Path, stage_id: str | None = None) -> dict[str, Any]:
        return import_funnel_result(
            ticker, source, stage_id=stage_id, store=self.store, workspace_root=self.workspace_root,
        )

    def funnel_status(self, ticker: str) -> str:
        p = self.get(ticker)
        if not p:
            return "NOT_FOUND"
        sync_completion_fields(p, store=self.store, workspace_root=self.workspace_root)
        completion = p.funnel_completion_status
        if completion == FUNNEL_COMPLETION_COMPLETE:
            if p.delta_eligible == DELTA_ELIGIBLE_YES:
                return "CURRENT" if p.last_valuation_date else "NEEDS_DELTA"
            return "NEEDS_DELTA"
        if completion == FUNNEL_COMPLETION_PARTIAL:
            return "PARTIAL"  # Explorer alias: REQUIRES_CONTINUATION
        if completion == FUNNEL_COMPLETION_NOT_STARTED:
            return "NOT_FOUND"
        return "NOT_FOUND"

    def context_fields(self, ticker: str) -> dict[str, Any]:
        """Selected Funnel fields for Explorer context only — never recalculated here."""
        status = self.funnel_status(ticker)
        # Map PARTIAL → also expose REQUIRES_CONTINUATION for consumers
        explorer_status = "REQUIRES_CONTINUATION" if status == "PARTIAL" else status
        kv = self.store.all_key_values(ticker) if self.store else {}
        p = self.get(ticker)
        if p:
            sync_completion_fields(p, store=self.store, workspace_root=self.workspace_root)
        fv = sanitize_fair_value(kv.get("Fair Value") or kv.get("Blended Fair Value"))
        return {
            "ticker": ticker.upper(),
            "funnel_status": explorer_status,
            "funnel_completion_status": getattr(p, "funnel_completion_status", None) if p else "NOT_STARTED",
            "delta_eligible": getattr(p, "delta_eligible", None) if p else "NO",
            "verified_completed_stages": list(getattr(p, "verified_completed_stages", None) or []) if p else [],
            "valuation_status": p.valuation_status if p else None,
            "Business Quality": kv.get("Business Quality"),
            "Earnings Quality": kv.get("Earnings Quality"),
            "Financial Strength": kv.get("Financial Strength"),
            "Growth": kv.get("Growth"),
            "Economic Valuation": kv.get("Economic Valuation"),
            "Fair Value Range": fv,
            "Investment Classification": kv.get("Investment Classification"),
            "Integrated Risk": kv.get("Integrated Risk"),
            "Valuation Date": kv.get("Valuation date") or (p.last_valuation_date if p else None),
            "Final Decision Domain": kv.get("Final Decision Domain") or kv.get("Final Decision"),
            "structured_fields": p.structured_fields if p else {},
            "structured_provenance": p.structured_provenance if p else {},
            "funnel_version": p.funnel_version if p else None,
            "decision_kind": "IMPORTED_LLM_DECISION" if p and p.structured_fields.get("final_decision") else None,
            "note": "Context only — Explorer must not modify these values",
        }
