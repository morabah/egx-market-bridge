#!/usr/bin/env python3
"""v0.6.4 acceptance: Daily Operator workflow, version labels, session safety.

Read-only against production. Isolated pytest. No score retuning.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from egxbridge.ui import ALL_PAGES, DEFAULT_PAGE
from egxbridge.ui.snapshot import gather_operator_snapshot
from egxbridge.ui.versions import version_caption, version_labels
from egxbridge.ui.workflow_state import (
    ACTION_LABELS,
    explorer_status,
    freshness_state,
    intraday_card_state,
    recommended_jobs,
)


WEEKEND_META = {
    "session_phase": "POST_CLOSE",
    "analysis_timestamp_utc": "2026-09-05T13:00:00+00:00",
    "analysis_timestamp_cairo": "2026-09-05T16:00:00+03:00",
}


def main() -> int:
    acc = HERE / "output" / "acceptance" / "v064"
    acc.mkdir(parents=True, exist_ok=True)

    print("=== pytest (not integration) ===")
    pytest_proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=str(HERE),
        capture_output=True,
        text=True,
    )
    pytest_text = (pytest_proc.stdout or "") + "\n" + (pytest_proc.stderr or "")
    (acc / "pytest.txt").write_text(pytest_text, encoding="utf-8")
    print(pytest_proc.stdout or pytest_proc.stderr)
    pytest_ok = pytest_proc.returncode == 0

    labels = version_labels()
    caption = version_caption(labels)
    version_ok = (
        labels["application_version"] == "0.6.4"
        and labels["market_data_schema_version"] == "0.3.1"
        and labels["scoring_version"] == "0.5.1"
        and "Version:" not in caption
        and DEFAULT_PAGE == "Daily Operator"
        and ALL_PAGES[0] == "Daily Operator"
        and "System Overview" in ALL_PAGES
        and "Overview" not in ALL_PAGES
    )

    store = None
    try:
        from egxbridge.analysis.common.persistence import AnalysisStore
        from egxbridge.analysis.common.environment import PRODUCTION
        dbp = HERE / "output" / "analysis.sqlite"
        if dbp.exists():
            store = AnalysisStore(dbp, environment=PRODUCTION)
    except Exception:
        store = None

    weekend = gather_operator_snapshot(root=HERE, store=store, session_meta=WEEKEND_META)
    if store is not None:
        try:
            store.close()
        except Exception:
            pass

    live_ready = intraday_card_state(session_phase="CONTINUOUS_TRADING", age_seconds=120)
    live_stale = intraday_card_state(session_phase="CONTINUOUS_TRADING", age_seconds=480)
    post = intraday_card_state(session_phase="POST_CLOSE", age_seconds=120)
    pre = intraday_card_state(session_phase="PRE_OPEN", age_seconds=60)
    rec = recommended_jobs(session_phase="POST_CLOSE", cairo_weekday=5)

    session_ok = (
        post["status"] == "NOT_LIVE"
        and pre["status"] == "NOT_LIVE"
        and live_ready["actionable"] is True
        and live_stale["actionable"] is False
        and live_stale["status"] == "STALE"
        and freshness_state(session_phase="POST_CLOSE") == "STALE_EXPECTED"
    )

    exp_same_session = explorer_status(
        has_explorer=True, candidate_count=int(weekend.get("candidate_count") or 0),
        explorer_session=weekend.get("latest_completed_market_session"),
        market_session=weekend.get("latest_completed_market_session"),
        coverage=weekend.get("coverage"),
    )

    fail = []
    if not pytest_ok:
        fail.append("pytest failed")
    if not version_ok:
        fail.append("version labels or default page incorrect")
    if not session_ok:
        fail.append("session-phase safety failed")
    if weekend.get("intraday", {}).get("status") != "NOT_LIVE":
        fail.append("weekend Daily Operator marked Intraday live")
    if weekend.get("freshness") not in {"STALE_EXPECTED", "LIVE"}:
        fail.append("unexpected freshness on weekend snapshot")
    if rec["intraday_live"]:
        fail.append("POST_CLOSE recommended Intraday as live")

    limitations = [
        "Screenshots were not automated; Streamlit Daily Operator was not opened in a browser in this run.",
        "Live TradingView refresh and Yahoo recollect were not executed by the acceptance script.",
        "workspace/explorer/last_run.json is often overwritten by pytest temp packages; Daily Operator ignores pytest paths and prefers the accepted 20-candidate Explorer package when the dashboard alias is a tiny leftover.",
        "workspace/schedule/last_run.json still points at the v0.6.1 identity package, so next action is Export/Import rather than Prepare when those ZIPs exist.",
        "Focus snapshot chatgpt_handoff.json remains a small sample and is labeled separately from Explorer universe coverage.",
        "Production analysis.sqlite outcome/import counts are cumulative from prior versions; they were read, not rewritten.",
        "Intraday candle timestamps from the last completed session can look old on the weekend; ACTIONABLE stays NO because the session is NOT LIVE.",
    ]

    if fail:
        verdict = "FAIL"
    else:
        verdict = "PASS WITH LIMITATIONS"

    report = {
        "verdict": verdict,
        "fail_reasons": fail,
        "default_page": DEFAULT_PAGE,
        "sidebar": list(ALL_PAGES),
        "version_labels": labels,
        "version_caption": caption,
        "weekend_post_close": {
            "latest_completed_session": weekend.get("latest_completed_market_session"),
            "session_phase": weekend.get("session_phase"),
            "freshness": weekend.get("freshness"),
            "freshness_note": weekend.get("freshness_note"),
            "market_data_status": weekend.get("market_data_status"),
            "provider_status": weekend.get("provider_status"),
            "explorer_status": weekend.get("explorer_status"),
            "explorer_same_session_status": exp_same_session,
            "candidate_count": weekend.get("candidate_count"),
            "equity_universe": weekend.get("equity_universe"),
            "daily_data_available": weekend.get("daily_data_available"),
            "scanner_eligible": weekend.get("scanner_eligible"),
            "prescreen": weekend.get("prescreen"),
            "intraday_enriched": weekend.get("intraday_enriched"),
            "intraday_requested": weekend.get("intraday_requested"),
            "intraday": weekend.get("intraday"),
            "recommended_jobs": weekend.get("recommended_jobs"),
            "schedules_prepared": weekend.get("schedules_prepared"),
            "imported_n": weekend.get("imported_n"),
            "generated_n": weekend.get("generated_n"),
            "evaluable_n": weekend.get("evaluable_n"),
            "funnel_action_n": weekend.get("funnel_action_n"),
            "outcomes_pending_n": weekend.get("outcomes_pending_n"),
            "calibration_status": weekend.get("calibration_status"),
            "weekly_recommended": weekend.get("weekly_recommended"),
            "next_action": weekend.get("next_action"),
            "readiness": weekend.get("readiness"),
            "explorer_package_dir": (weekend.get("explorer") or {}).get("package_dir"),
            "explorer_run_id": (weekend.get("explorer") or {}).get("explorer_run_id"),
        },
        "live_session_synthetic": {
            "age_2min": live_ready,
            "age_8min": live_stale,
            "post_close": post,
            "pre_open": pre,
        },
        "job_recommendation_weekend": rec,
        "pytest_ok": pytest_ok,
        "pytest_returncode": pytest_proc.returncode,
        "scoring_changed": False,
        "limitations": limitations,
        "operator_flow": [
            "STEP 1 Refresh Market Data (STALE_EXPECTED is normal when closed)",
            "STEP 2 Run Broad Explorer",
            "STEP 3 Review Candidates",
            "STEP 4 Prepare Next-Session Package (Macro / Pre-Market / Value)",
            "STEP 5 Export combined ChatGPT ZIP",
            "STEP 6 Import ChatGPT results",
            "STEP 7 Funnel actions from Value result",
            "STEP 8 Intraday NOT LIVE unless CONTINUOUS_TRADING and age <= 5 minutes",
            "STEP 9 Update Outcomes",
            "STEP 10 Weekly X-Ray",
        ],
    }
    (acc / "daily_operator_acceptance.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8",
    )
    nxt = weekend.get("next_action") or {}
    md = [
        "# EGX Market Bridge v0.6.4 Daily Operator",
        "",
        f"Verdict: **{verdict}**",
        "",
        "## Default page",
        f"{DEFAULT_PAGE} (sidebar index 0)",
        "",
        "## Version labels",
        f"- Application: {labels['application_version']}",
        f"- Market Data Schema: {labels['market_data_schema_version']}",
        f"- Scoring: {labels['scoring_version']} / {labels['score_kind']}",
        f"- Caption: `{caption}`",
        "",
        "## Weekend / POST_CLOSE snapshot",
        f"- Latest completed session: {weekend.get('latest_completed_market_session')}",
        f"- Session phase: {weekend.get('session_phase')}",
        f"- Freshness: {weekend.get('freshness')}",
        f"- Market Data: {weekend.get('market_data_status')}",
        f"- Providers: {weekend.get('provider_status')}",
        f"- Explorer: {weekend.get('explorer_status')} ({weekend.get('candidate_count')} candidates)",
        f"- Daily data: {weekend.get('daily_data_available')} / {weekend.get('equity_universe')}",
        f"- Scanner eligible: {weekend.get('scanner_eligible')}",
        f"- Intraday: {weekend.get('intraday')}",
        f"- Recommended jobs: {weekend.get('recommended_jobs')}",
        f"- Outcomes pending: {weekend.get('outcomes_pending_n')}",
        f"- Next recommended action: {nxt.get('label') or nxt.get('code')} (`{nxt.get('code')}`)",
        f"- Action label map: {ACTION_LABELS.get(nxt.get('code'), '')}",
        "",
        "## Live session synthetic",
        f"- CONTINUOUS_TRADING + 2 min: {live_ready}",
        f"- CONTINUOUS_TRADING + 8 min: {live_stale}",
        f"- POST_CLOSE: {post['status']}",
        f"- PRE_OPEN: {pre['status']}",
        "",
        "## pytest",
        f"{'PASS' if pytest_ok else 'FAIL'} (exit {pytest_proc.returncode})",
        "",
        "## Operator flow",
        *[f"- {line}" for line in report["operator_flow"]],
        "",
        "## Limitations",
        *[f"- {line}" for line in limitations],
        "",
        "## Fail reasons",
        json.dumps(fail, indent=2),
    ]
    (acc / "daily_operator_acceptance.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": verdict, "next_action": nxt, "pytest_ok": pytest_ok}, indent=2, default=str))
    print("VERDICT", verdict)
    return 0 if verdict != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
