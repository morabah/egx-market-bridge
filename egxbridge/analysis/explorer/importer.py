from __future__ import annotations

from pathlib import Path
from typing import Any

from egxbridge import __version__ as BRIDGE_VERSION
from egxbridge.analysis.common.models import utc_now, content_hash, AnalysisProvenance
from egxbridge.analysis.common.packaging import write_text, write_json
from egxbridge.analysis.common.persistence import AnalysisStore


HERE = Path(__file__).resolve().parents[3]


def import_explorer_result(
    source: Path | str,
    *,
    store: AnalysisStore | None = None,
    horizon: str = "NEXT_WORKING_DAY",
) -> dict[str, Any]:
    path = Path(source) if not isinstance(source, str) or Path(source).exists() else None
    if path and path.exists():
        content = path.read_text(encoding="utf-8")
        source_file = str(path)
    else:
        content = str(source)
        source_file = "pasted_text"

    h = content_hash(content)
    dest = HERE / "workspace" / "explorer" / "imports"
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / f"explorer_result_{h[:12]}.md"
    write_text(out, content)

    if store:
        prov = AnalysisProvenance(
            analysis_type="EXPLORER",
            ticker_or_universe="EGX_UNIVERSE",
            generated_at=utc_now(),
            imported_at=utc_now(),
            bridge_version=BRIDGE_VERSION,
            source_file=source_file,
            content_hash=h,
            run_mode=horizon,
        )
        store.record_import(prov.to_dict(), content)

    return {
        "saved_path": str(out),
        "content_hash": h,
        "original_preserved": True,
        "orders_generated": False,
        "modifies_funnel_fair_value": False,
    }
