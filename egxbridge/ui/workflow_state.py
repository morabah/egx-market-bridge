"""Derived Daily Operator workflow state. UI orchestration only — no scoring."""
from __future__ import annotations

from typing import Any


LIVE_PHASES = {"CONTINUOUS_TRADING", "CLOSING_AUCTION", "TRADING_AT_LAST"}
STALE_EXPECTED_PHASES = {"POST_CLOSE", "PRE_OPEN"}
NEXT_SESSION_JOBS = ("MACRO_HOLDINGS", "PREMARKET_CATALYSTS", "VALUE_QUALITY")
ALL_JOBS = (
    "MACRO_HOLDINGS",
    "PREMARKET_CATALYSTS",
    "INTRADAY_OPPORTUNITY",
    "VALUE_QUALITY",
    "WEEKLY_XRAY",
)
JOB_LABELS = {
    "MACRO_HOLDINGS": "Macro / Holdings",
    "PREMARKET_CATALYSTS": "Pre-Market Catalysts",
    "INTRADAY_OPPORTUNITY": "Intraday Opportunity",
    "VALUE_QUALITY": "Value & Quality",
    "WEEKLY_XRAY": "Weekly X-Ray",
}
INTRADAY_ACTIONABLE_MAX_AGE_SECONDS = 300

ACTION_REFRESH_MARKET_DATA = "REFRESH_MARKET_DATA"
ACTION_RUN_EXPLORER = "RUN_EXPLORER"
ACTION_REVIEW_CANDIDATES = "REVIEW_CANDIDATES"
ACTION_PREPARE_NEXT_SESSION = "PREPARE_NEXT_SESSION"
ACTION_EXPORT_OR_IMPORT = "EXPORT_OR_IMPORT_CHATGPT"
ACTION_IMPORT_CHATGPT = "IMPORT_CHATGPT_RESULTS"
ACTION_FUNNEL = "FUNNEL_ACTION_REQUIRED"
ACTION_INTRADAY = "REFRESH_OR_PREPARE_INTRADAY"
ACTION_UPDATE_OUTCOMES = "UPDATE_OUTCOMES"
ACTION_WEEKLY = "PREPARE_WEEKLY_REVIEW"
ACTION_WAIT = "WAIT_FOR_FUTURE_SESSIONS"

ACTION_LABELS = {
    ACTION_REFRESH_MARKET_DATA: "Scan the market",
    ACTION_RUN_EXPLORER: "Scan the EGX universe",
    ACTION_REVIEW_CANDIDATES: "Review your candidates",
    ACTION_PREPARE_NEXT_SESSION: "Build the ChatGPT package",
    ACTION_EXPORT_OR_IMPORT: "Send the package to ChatGPT",
    ACTION_IMPORT_CHATGPT: "Import ChatGPT results",
    ACTION_FUNNEL: "Continue company valuation",
    ACTION_INTRADAY: "Refresh live Intraday evidence",
    ACTION_UPDATE_OUTCOMES: "Update signal outcomes",
    ACTION_WEEKLY: "Prepare the weekly review",
    ACTION_WAIT: "Wait for the next completed session",
}

ACTION_CTA = {
    ACTION_REFRESH_MARKET_DATA: "Refresh and scan Explorer",
    ACTION_RUN_EXPLORER: "Run Broad Explorer",
    ACTION_REVIEW_CANDIDATES: "Open candidate list",
    ACTION_PREPARE_NEXT_SESSION: "Prepare next-session package",
    ACTION_EXPORT_OR_IMPORT: "Download EGX_CHATGPT_HANDOFF.zip",
    ACTION_IMPORT_CHATGPT: "Import this ChatGPT file",
    ACTION_FUNNEL: "Prepare Funnel for the named ticker",
    ACTION_INTRADAY: "Refresh Intraday evidence",
    ACTION_UPDATE_OUTCOMES: "Update signal outcomes",
    ACTION_WEEKLY: "Prepare Weekly X-Ray",
    ACTION_WAIT: None,
}

FUNNEL_START = {"START_FULL_FUNNEL", "NEEDS_FULL_FUNNEL", "PREPARE_FULL_FUNNEL"}
FUNNEL_CONTINUE = {"CONTINUE_FUNNEL"}
FUNNEL_DELTA = {"RUN_DELTA", "PREPARE_DELTA", "NEEDS_FUNNEL_DELTA"}
FUNNEL_VIEW_ONLY = {"NO_ACTION", "REVIEW_EXISTING_FUNNEL", "NO_FUNNEL_ACTION"}


def is_weekend(cairo_weekday: int | None) -> bool:
    return cairo_weekday in (4, 5)  # Friday / Saturday, consistent with the session clock.


def freshness_state(*, session_phase: str | None, unexpected_stale: bool = False) -> str:
    phase = session_phase or "UNKNOWN"
    if unexpected_stale and phase in LIVE_PHASES:
        return "UNEXPECTED_STALE"
    if phase in STALE_EXPECTED_PHASES or phase == "UNKNOWN":
        return "STALE_EXPECTED"
    if phase in LIVE_PHASES:
        return "LIVE"
    return "STALE_EXPECTED"


def freshness_note(state: str, *, session_phase: str | None = None) -> str:
    if state == "STALE_EXPECTED":
        return (
            "Market is currently closed. Latest completed session data is expected to be "
            "stale and remains valid for next-session research."
        )
    if state == "UNEXPECTED_STALE":
        return "Market appears live, but collected evidence looks unexpectedly stale."
    if state == "LIVE":
        return f"Session phase is {session_phase or 'live'}."
    return ""


def explorer_status(
    *,
    has_explorer: bool,
    candidate_count: int,
    explorer_session: str | None,
    market_session: str | None,
    coverage: str | None = None,
    failed: bool = False,
) -> str:
    if failed:
        return "FAILED"
    if not has_explorer:
        return "NOT_RUN"
    if explorer_session and market_session and explorer_session != market_session:
        return "STALE"
    if coverage == "INSUFFICIENT" or candidate_count <= 0:
        return "PARTIAL"
    return "READY"


def intraday_card_state(
    *,
    session_phase: str | None,
    age_seconds: float | None = None,
    max_age: int = INTRADAY_ACTIONABLE_MAX_AGE_SECONDS,
) -> dict[str, Any]:
    phase = session_phase or "UNKNOWN"
    live = phase == "CONTINUOUS_TRADING"
    if not live:
        return {
            "live": False,
            "actionable": False,
            "status": "NOT_LIVE",
            "headline": (
                "Live intraday confirmation is not currently available because the market "
                "is not in continuous trading."
            ),
            "age_seconds": age_seconds,
        }
    stale = age_seconds is None or age_seconds > max_age
    if stale:
        return {
            "live": True,
            "actionable": False,
            "status": "STALE",
            "headline": "Intraday evidence is too stale for actionable confirmation.",
            "age_seconds": age_seconds,
        }
    return {
        "live": True,
        "actionable": True,
        "status": "READY",
        "headline": "Live session — refresh Intraday evidence before confirmation analysis.",
        "age_seconds": age_seconds,
    }


def recommended_jobs(*, session_phase: str | None, cairo_weekday: int | None = None) -> dict[str, Any]:
    phase = session_phase or "POST_CLOSE"
    weekend = is_weekend(cairo_weekday)
    weekly = weekend or cairo_weekday == 4  # Friday after close, or weekend review
    if phase == "CONTINUOUS_TRADING":
        rec = ["INTRADAY_OPPORTUNITY"]
        optional = ["MACRO_HOLDINGS", "PREMARKET_CATALYSTS"]
        return {
            "recommended": rec,
            "optional": optional,
            "next_session": list(NEXT_SESSION_JOBS),
            "weekly_recommended": False,
            "intraday_live": True,
        }
    if phase == "PRE_OPEN":
        return {
            "recommended": ["MACRO_HOLDINGS", "PREMARKET_CATALYSTS", "VALUE_QUALITY"],
            "optional": ["WEEKLY_XRAY"] if weekly else [],
            "next_session": list(NEXT_SESSION_JOBS),
            "weekly_recommended": weekly,
            "intraday_live": False,
        }
    # POST_CLOSE / weekend / auction
    rec = ["MACRO_HOLDINGS", "PREMARKET_CATALYSTS", "VALUE_QUALITY"]
    return {
        "recommended": rec,
        "optional": ["WEEKLY_XRAY"] if weekly else ["WEEKLY_XRAY"],
        "next_session": list(NEXT_SESSION_JOBS),
        "weekly_recommended": weekly,
        "intraday_live": False,
        "intraday_note": "NOT LIVE — historical review only, not execution confirmation.",
    }


def job_applicable_now(job: str, *, session_phase: str | None, cairo_weekday: int | None = None) -> bool:
    rec = recommended_jobs(session_phase=session_phase, cairo_weekday=cairo_weekday)
    if job in rec["recommended"]:
        return True
    if job == "INTRADAY_OPPORTUNITY":
        return True  # always manually available as review
    if job == "WEEKLY_XRAY":
        return True
    return job in rec["next_session"]


def funnel_buttons_for_status(funnel_status: str | None, chatgpt_action: str | None = None) -> list[str]:
    action = (chatgpt_action or "").strip().upper() or None
    st = (funnel_status or "NOT_FOUND").upper()
    if st in {"COMPLETE", "CURRENT"}:
        st = "CURRENT"
    buttons: list[str] = []
    if st == "NOT_FOUND" or action in FUNNEL_START:
        buttons.append("PREPARE_FULL_FUNNEL")
    if st in {"PARTIAL", "REQUIRES_CONTINUATION"} or action in FUNNEL_CONTINUE:
        buttons.append("CONTINUE_FUNNEL")
    if st in {"NEEDS_DELTA", "STALE"} or action in FUNNEL_DELTA:
        buttons.append("PREPARE_DELTA")
    buttons.append("VIEW_FUNNEL")
    return list(dict.fromkeys(buttons))


def workflow_stage(snapshot: dict[str, Any]) -> str:
    if not snapshot.get("data_usable"):
        return "DATA_NOT_READY"
    if snapshot.get("explorer_status") in {None, "NOT_RUN"}:
        return "EXPLORER_NOT_RUN"
    if snapshot.get("explorer_status") == "STALE":
        return "EXPLORER_NOT_RUN"
    if not snapshot.get("schedules_prepared"):
        return "SCHEDULES_NOT_PREPARED"
    imported = int(snapshot.get("recommended_imported_n") or 0)
    needed = int(snapshot.get("recommended_jobs_n") or 0)
    if needed and imported < needed:
        return "RESULTS_PARTIAL"
    if snapshot.get("funnel_action_required"):
        return "FUNNEL_ACTION_REQUIRED"
    intra = snapshot.get("intraday") or {}
    if intra.get("live") and intra.get("actionable"):
        return "INTRADAY_READY"
    if snapshot.get("outcomes_pending_n"):
        return "OUTCOMES_PENDING"
    if snapshot.get("weekly_recommended"):
        return "WEEKLY_REVIEW_READY"
    if imported >= needed and needed:
        return "RESULTS_IMPORTED"
    return "EXPLORER_READY"


def next_recommended_action(snapshot: dict[str, Any]) -> dict[str, str]:
    """Derive the single next operator action from actual state."""
    intra = snapshot.get("intraday") or {}
    if not snapshot.get("data_usable"):
        code = ACTION_REFRESH_MARKET_DATA
    elif snapshot.get("explorer_status") in {None, "NOT_RUN", "FAILED"}:
        code = ACTION_RUN_EXPLORER
    elif snapshot.get("explorer_status") == "STALE":
        code = ACTION_RUN_EXPLORER
    elif not snapshot.get("schedules_prepared"):
        code = ACTION_PREPARE_NEXT_SESSION
    elif int(snapshot.get("recommended_imported_n") or 0) < int(snapshot.get("recommended_jobs_n") or 1):
        imported = int(snapshot.get("recommended_imported_n") or 0)
        if imported > 0 or snapshot.get("ready_to_import"):
            code = ACTION_IMPORT_CHATGPT
        else:
            code = ACTION_EXPORT_OR_IMPORT
    elif snapshot.get("funnel_action_required"):
        code = ACTION_FUNNEL
    elif intra.get("live"):
        code = ACTION_INTRADAY
    elif snapshot.get("outcomes_update_recommended"):
        code = ACTION_UPDATE_OUTCOMES
    elif snapshot.get("weekly_recommended") and not snapshot.get("weekly_imported"):
        code = ACTION_WEEKLY
    elif snapshot.get("outcomes_pending_n") and snapshot.get("weekend"):
        code = ACTION_WAIT
    elif snapshot.get("candidate_count"):
        code = ACTION_REVIEW_CANDIDATES
    else:
        code = ACTION_REFRESH_MARKET_DATA
    return {
        "code": code,
        "label": ACTION_LABELS.get(code, code),
        "stage": workflow_stage(snapshot),
    }


def build_step_statuses(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Compact statuses for the ten Daily Operator steps."""
    data = snapshot.get("market_data_status")
    if not data:
        data = "READY" if snapshot.get("data_usable") else "NOT RUN"
    if snapshot.get("freshness") == "STALE_EXPECTED" and snapshot.get("data_usable") and data == "NOT RUN":
        data = "READY"
    explorer = snapshot.get("explorer_status") or "NOT_RUN"
    schedules = "READY" if snapshot.get("schedules_prepared") else "NOT PREPARED"
    imported_n = int(snapshot.get("recommended_imported_n") or snapshot.get("imported_n") or 0)
    needed_n = int(snapshot.get("recommended_jobs_n") or 0)
    if not needed_n:
        included = ((snapshot.get("schedule") or {}).get("included_jobs") if isinstance(snapshot.get("schedule"), dict) else None) or []
        needed_n = len(included) or 5
    chatgpt = f"{imported_n}/{needed_n} IMPORTED" if snapshot.get("schedules_prepared") else "NOT IMPORTED"
    funnel_n = int(snapshot.get("funnel_action_n") or 0)
    funnel = f"ACTION REQUIRED: {funnel_n}" if funnel_n else "NO ACTION"
    pending = int(snapshot.get("outcomes_pending_n") or 0)
    outcomes = f"{pending} PENDING" if pending else "NONE"
    intra = snapshot.get("intraday") or {}
    return [
        {"id": "market_data", "label": "Market Data", "status": data},
        {"id": "explorer", "label": "Explorer", "status": explorer},
        {"id": "schedules", "label": "Schedules", "status": schedules},
        {"id": "chatgpt", "label": "ChatGPT Imports", "status": chatgpt},
        {"id": "funnel", "label": "Funnel", "status": funnel},
        {"id": "outcomes", "label": "Outcomes", "status": outcomes},
        {"id": "intraday", "label": "Intraday", "status": intra.get("status") or "NOT_LIVE"},
    ]


def daily_bars_already_usable(snapshot: dict[str, Any], *, min_eligible: int = 30) -> bool:
    if not snapshot.get("data_usable"):
        return False
    eligible = int(snapshot.get("scanner_eligible") or 0)
    daily = int(snapshot.get("daily_data_available") or 0)
    return eligible >= min_eligible or daily >= min_eligible


def should_skip_market_refresh(snapshot: dict[str, Any]) -> bool:
    """Closed/weekend: latest completed session bars remain valid. Do not refetch Yahoo."""
    if not daily_bars_already_usable(snapshot):
        return False
    return snapshot.get("freshness") == "STALE_EXPECTED" or snapshot.get("session_phase") in STALE_EXPECTED_PHASES


def explorer_should_enrich_intraday(session_phase: str | None, *, force: bool = False) -> bool:
    """TV enrichment is post-score packaging. Skip it unless the cash market is live or forced."""
    if force:
        return True
    return session_phase == "CONTINUOUS_TRADING"


ACTION_TO_STEPS = {
    ACTION_REFRESH_MARKET_DATA: {1},
    ACTION_RUN_EXPLORER: {2},
    ACTION_REVIEW_CANDIDATES: {3},
    ACTION_PREPARE_NEXT_SESSION: {4},
    ACTION_EXPORT_OR_IMPORT: {5},
    ACTION_IMPORT_CHATGPT: {6},
    ACTION_FUNNEL: {7},
    ACTION_INTRADAY: {8},
    ACTION_UPDATE_OUTCOMES: {9},
    ACTION_WAIT: {9},
    ACTION_WEEKLY: {10},
}


def focus_steps(action_code: str | None) -> set[int]:
    return set(ACTION_TO_STEPS.get(action_code or "", {1}))


def action_hint(code: str | None, snapshot: dict[str, Any] | None = None) -> str:
    snap = snapshot or {}
    if code == ACTION_REFRESH_MARKET_DATA and should_skip_market_refresh(snap):
        return (
            "Market is closed. Cached daily bars stay valid — scan Explorer without refetching Yahoo."
        )
    if code == ACTION_RUN_EXPLORER and snap.get("freshness") == "STALE_EXPECTED":
        return snap.get("freshness_note") or (
            "Market is closed. Latest completed session remains valid for next-session research."
        )
    hints = {
        ACTION_REFRESH_MARKET_DATA: "Collect the latest available snapshot, then scan Explorer.",
        ACTION_RUN_EXPLORER: "Daily bars are usable. Scan the eligible universe next.",
        ACTION_REVIEW_CANDIDATES: "Rank is a screening priority, not a buy recommendation.",
        ACTION_PREPARE_NEXT_SESSION: "Build Macro, Pre-Market, and Value/Quality into one ChatGPT ZIP.",
        ACTION_EXPORT_OR_IMPORT: "Download one ZIP. Upload that file in ChatGPT. Do not import yet.",
        ACTION_IMPORT_CHATGPT: "Upload each saved ChatGPT reply. The ZIP you downloaded is not a result.",
        ACTION_FUNNEL: "Value & Quality asked for a company valuation. Fair Value is never calculated here.",
        ACTION_INTRADAY: "Continuous trading is open. Refresh evidence before confirmation analysis.",
        ACTION_UPDATE_OUTCOMES: "Calculate returns after 1, 2, 5, 10 and 20 trading sessions, plus the best and worst price moves.",
        ACTION_WEEKLY: "Historical review only. Scoring stays frozen at 0.5.1 / HEURISTIC_UNCALIBRATED.",
        ACTION_WAIT: "Wait for a completed session before updating outcomes.",
    }
    return hints.get(code or "", "")


def action_steps(code: str | None, snapshot: dict[str, Any] | None = None) -> list[str]:
    snap = snapshot or {}
    jobs = snap.get("schedule", {}).get("included_jobs") if isinstance(snap.get("schedule"), dict) else None
    jobs = jobs or list(NEXT_SESSION_JOBS)
    job_txt = ", ".join(JOB_LABELS.get(j, j) for j in jobs)
    steps = {
        ACTION_REFRESH_MARKET_DATA: [
            "Collect available market data and create a ranked candidate list for review.",
            "The scan automatically saves the starting evidence for future outcome tracking.",
        ],
        ACTION_RUN_EXPLORER: [
            "Your daily data is ready. Scan the eligible stocks to create your candidate list.",
        ],
        ACTION_REVIEW_CANDIDATES: [
            "Open the candidate list. Rank is screening priority, not a buy order.",
        ],
        ACTION_PREPARE_NEXT_SESSION: [
            "Create the evidence package that ChatGPT needs for analysis.",
            f"Included analyses: {job_txt}.",
        ],
        ACTION_EXPORT_OR_IMPORT: [
            "Download EGX_CHATGPT_HANDOFF.zip, then attach it to a ChatGPT conversation.",
            f"Ask ChatGPT to run {job_txt}.",
            "Save each reply as .md, .txt or .json and return here to import it. Do not import the ZIP; company Funnel replies use Analysis Workflows.",
        ],
        ACTION_IMPORT_CHATGPT: [
            "Choose the analysis that matches your saved ChatGPT reply.",
            "Upload the saved ChatGPT reply, then press Import this ChatGPT file.",
            "Repeat for each job. Do not upload EGX_CHATGPT_HANDOFF.zip.",
        ],
        ACTION_FUNNEL: [
            "Review the requested company analysis and continue its Funnel in ChatGPT.",
            "The app prepares the evidence; ChatGPT supplies the valuation and expectations judgments.",
        ],
        ACTION_INTRADAY: [
            "Press Refresh Intraday evidence. Confirmation is only valid in continuous trading with fresh bars.",
        ],
        ACTION_UPDATE_OUTCOMES: [
            "Calculate returns after 1, 2, 5, 10 and 20 completed trading sessions.",
            "Future horizons stay pending. Best and worst price moves are calculated from available highs and lows.",
        ],
        ACTION_WEEKLY: [
            "Package forward outcomes, missed candidates and sample limitations for ChatGPT's weekly review.",
            "Any proposed rule changes are saved for human review.",
        ],
        ACTION_WAIT: [
            "Your signals are saved. Their future returns need another completed trading session.",
            "After the next session, refresh market data and update outcomes.",
        ],
    }
    return list(steps.get(code or "", []))
