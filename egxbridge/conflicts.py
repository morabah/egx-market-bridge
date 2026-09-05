from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any

from .semantics import (
    volumes_comparable,
    is_daily_session_label,
    effective_session_date_of,
)
from .quality import PROVIDER_RELIABILITY


@dataclass
class ConflictRecord:
    symbol: str
    field: str
    provider_a: str
    value_a: Any
    timestamp_a: str | None
    provider_b: str
    value_b: Any
    timestamp_b: str | None
    selected_provider: str
    reason: str
    created_at: str
    volume_semantics: str | None = None
    interval: str | None = None
    session_date: str | None = None


@dataclass
class SelectionResult:
    selected_provider: str
    selected_value: Any
    selected_timestamp: str | None
    reason: str
    conflict: ConflictRecord | None = None
    candidates: list[dict[str, Any]] = field(default_factory=list)
    skipped_incomparable: list[dict[str, Any]] = field(default_factory=list)


def values_conflict(a: Any, b: Any, *, rel_tol: float = 0.002, abs_tol: float = 0.01) -> bool:
    if a is None or b is None:
        return False
    try:
        fa, fb = float(a), float(b)
    except Exception:
        return str(a) != str(b)
    if fa == fb:
        return False
    diff = abs(fa - fb)
    scale = max(abs(fa), abs(fb), 1e-9)
    return diff > abs_tol and (diff / scale) > rel_tol


def _session_rank(sess: str | None) -> int:
    """Newer session_date sorts first (smaller key). Missing sessions sort last."""
    if not sess:
        return 0
    try:
        return -date.fromisoformat(sess).toordinal()
    except Exception:
        return 0


def select_observation(
    candidates: list[dict[str, Any]],
    *,
    priority: list[str],
    created_at: str,
    field: str = "value",
    symbol: str = "",
    require_comparable_volume: bool = False,
) -> SelectionResult:
    """Choose one observation. Never averages.

    Daily-bar / DAILY_CLOSE / DAILY_FINAL_VOLUME observations are ranked by
    session_date + provider priority/reliability/completeness — never by
    arbitrary wall-clock labels (00:00 vs 10:00).

    Intraday BAR_VOLUME / candle closes continue to use timestamp freshness.
    """
    usable = [c for c in candidates if c.get("value") is not None]
    if not usable:
        return SelectionResult("", None, None, "no usable candidates", candidates=candidates)

    def rank(c: dict[str, Any]) -> tuple:
        prov = c.get("provider", "")
        try:
            prio = priority.index(prov)
        except ValueError:
            prio = 999
        reliability = -float(c.get("reliability_score") or PROVIDER_RELIABILITY.get(prov, 50.0))
        completeness = -int(c.get("completeness_score") or 0)
        if is_daily_session_label(c):
            sess = effective_session_date_of(c)
            # Daily session labels: priority → session_date → reliability/completeness.
            # Never wall-clock freshness.
            return (prio, _session_rank(sess), reliability, completeness, 0)
        age = c.get("freshness_seconds")
        age_key = age if isinstance(age, (int, float)) else 10**12
        # Intraday: priority then actual timestamp freshness.
        return (prio, age_key, 0, 0, 0)

    usable_sorted = sorted(usable, key=rank)
    best = usable_sorted[0]
    conflict = None
    skipped: list[dict[str, Any]] = []
    daily_best = is_daily_session_label(best)
    if daily_best:
        reason = (
            f"preferred by session_date/provider priority ({best.get('provider')}; "
            f"daily session label — wall-clock freshness ignored)"
        )
    else:
        reason = f"preferred by priority/freshness ({best.get('provider')})"

    for other in usable_sorted[1:]:
        if other.get("provider") == best.get("provider"):
            continue
        if field == "volume" or require_comparable_volume:
            if not volumes_comparable(best, other):
                skipped.append(
                    {
                        "provider": other.get("provider"),
                        "value": other.get("value"),
                        "volume_semantics": other.get("volume_semantics"),
                        "interval": other.get("interval"),
                        "session_date": effective_session_date_of(other) or other.get("session_date"),
                        "reason": "incomparable_volume_semantics",
                    }
                )
                continue
        if values_conflict(best.get("value"), other.get("value")):
            if daily_best and is_daily_session_label(other):
                reason = (
                    f"conflict: selected {best.get('provider')} over {other.get('provider')} "
                    f"by session_date/provider priority for same-session daily semantics; "
                    f"values not averaged; wall-clock labels not used for freshness"
                )
            else:
                reason = (
                    f"conflict: selected {best.get('provider')} "
                    f"(priority/freshness) over {other.get('provider')}; values not averaged"
                )
            conflict = ConflictRecord(
                symbol=symbol or str(best.get("symbol", "")),
                field=field,
                provider_a=str(best.get("provider")),
                value_a=best.get("value"),
                timestamp_a=best.get("provider_raw_timestamp")
                or best.get("provider_timestamp")
                or best.get("timestamp")
                or best.get("normalized_utc_timestamp"),
                provider_b=str(other.get("provider")),
                value_b=other.get("value"),
                timestamp_b=other.get("provider_raw_timestamp")
                or other.get("provider_timestamp")
                or other.get("timestamp")
                or other.get("normalized_utc_timestamp"),
                selected_provider=str(best.get("provider")),
                reason=reason,
                created_at=created_at,
                volume_semantics=best.get("volume_semantics") if field == "volume" else None,
                interval=best.get("interval"),
                session_date=effective_session_date_of(best) or best.get("session_date"),
            )
            break

    if skipped and field == "volume" and conflict is None:
        reason = (
            f"{reason}; skipped {len(skipped)} incomparable volume candidate(s) "
            f"(different semantics/interval/session)"
        )

    return SelectionResult(
        selected_provider=str(best.get("provider")),
        selected_value=best.get("value"),
        selected_timestamp=best.get("normalized_utc_timestamp")
        or best.get("provider_timestamp")
        or best.get("timestamp"),
        reason=reason,
        conflict=conflict,
        candidates=candidates,
        skipped_incomparable=skipped,
    )


def conflict_to_dict(c: ConflictRecord) -> dict[str, Any]:
    return asdict(c)
