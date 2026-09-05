from __future__ import annotations

from egxbridge.analysis.common.ai_mode import active_ai_mode, AI_CHATGPT_HANDOFF
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.funnel import FunnelRegistry
from egxbridge.analysis import WORKFLOW_VERSION, FUNNEL_PROMPT_VERSION

__all__ = [
    "active_ai_mode",
    "AI_CHATGPT_HANDOFF",
    "AnalysisStore",
    "FunnelRegistry",
    "ExplorerRegistry",
    "WORKFLOW_VERSION",
    "FUNNEL_PROMPT_VERSION",
]


def __getattr__(name: str):
    if name == "ExplorerRegistry":
        from egxbridge.analysis.explorer.registry import ExplorerRegistry
        return ExplorerRegistry
    raise AttributeError(name)

