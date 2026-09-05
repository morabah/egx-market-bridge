from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any
from datetime import datetime, timezone
import hashlib


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


@dataclass
class Availability:
    """Explicit missing-data vocabulary — never fabricate."""
    status: str  # AVAILABLE | UNAVAILABLE | NOT_RELIABLE | NOT_APPLICABLE
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisProvenance:
    analysis_type: str
    ticker_or_universe: str
    generated_at: str
    imported_at: str | None = None
    funnel_version: str | None = None
    bridge_version: str | None = None
    data_cutoff: str | None = None
    market_session: str | None = None
    source_file: str | None = None
    content_hash: str | None = None
    previous_analysis_id: str | None = None
    run_mode: str | None = None
    ai_mode: str = "CHATGPT_HANDOFF"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HandoffManifest:
    bridge_version: str
    workflow_type: str
    workflow_version: str
    generated_at: str
    ticker: str | None = None
    funnel_prompt_version: str | None = None
    analysis_objective: str | None = None
    run_mode: str | None = None
    data_cutoff: str | None = None
    latest_session: str | None = None
    research_data_quality: str | None = None
    execution_grade: str | None = None
    included_files: list[str] = field(default_factory=list)
    missing_capabilities: list[str] = field(default_factory=list)
    provider_summary: dict[str, Any] = field(default_factory=dict)
    previous_analysis_status: Any = None
    ai_mode: str = "CHATGPT_HANDOFF"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
