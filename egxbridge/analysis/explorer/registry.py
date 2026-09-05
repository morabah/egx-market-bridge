from __future__ import annotations

from pathlib import Path
from typing import Any

from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.explorer.models import ExplorerRunConfig
from egxbridge.analysis.explorer.handoff import prepare_explorer_handoff
from egxbridge.analysis.explorer.importer import import_explorer_result
from egxbridge.analysis.explorer.candidate_context import recommend_deep_analysis


from egxbridge.analysis.common.environment import PRODUCTION, normalize_environment


class ExplorerRegistry:
    def __init__(
        self,
        store: AnalysisStore | None = None,
        db=None,
        funnel_registry=None,
        environment: str | None = None,
    ):
        if environment is None:
            environment = getattr(store, "environment", None) or getattr(funnel_registry, "environment", None) or PRODUCTION
        self.environment = normalize_environment(environment)
        self.store = store
        self.db = db
        self.funnel_registry = funnel_registry


    def prepare(self, config: ExplorerRunConfig | None = None, output_root: Path | None = None) -> dict[str, Any]:
        return prepare_explorer_handoff(
            config, db=self.db, store=self.store, funnel_registry=self.funnel_registry, output_root=output_root,
        )

    def import_result(self, source: str | Path) -> dict[str, Any]:
        return import_explorer_result(source, store=self.store)

    def request_funnel_for_candidate(self, ticker: str, funnel_status: str | None = None) -> dict[str, Any]:
        status = funnel_status
        if status is None and self.funnel_registry:
            status = self.funnel_registry.funnel_status(ticker)
        status = status or "NOT_FOUND"
        rec = recommend_deep_analysis(status, high_interest=True)
        return {
            "ticker": ticker.upper(),
            "funnel_status": status,
            "recommended_deep_analysis": rec,
            "modifies_fair_value": False,
        }
