#!/usr/bin/env python3
"""Prepare 5-schedule ChatGPT handoffs. No paid LLM. scoring_version frozen at 0.5.1."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from egxbridge.analysis.common.environment import PRODUCTION, normalize_environment, analysis_db_path_for
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.schedule.types import JOB_ALIASES, ANALYSIS_TYPES
from egxbridge.analysis.schedule.handoff import prepare_schedule_handoffs


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Prepare EGX 5-schedule ChatGPT handoffs")
    p.add_argument("--job", default="all", help="all|macro|premarket|intraday|value|weekly")
    p.add_argument("--environment", default=PRODUCTION)
    p.add_argument("--from-explorer-dir", default="", help="Path to an Explorer package directory")
    p.add_argument("--output-root", default="")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--portfolio-context", default="")
    args = p.parse_args(argv)

    jobs = JOB_ALIASES.get(args.job)
    if jobs is None:
        if args.job in ANALYSIS_TYPES:
            jobs = [args.job]
        else:
            print("Unknown --job", args.job)
            return 2
    env = normalize_environment(args.environment)
    store = None if args.dry_run else AnalysisStore(analysis_db_path_for(env), environment=env)
    exp_dir = Path(args.from_explorer_dir) if args.from_explorer_dir else None
    out = Path(args.output_root) if args.output_root else None
    res = prepare_schedule_handoffs(
        explorer_package_dir=exp_dir,
        jobs=jobs,
        store=store,
        output_root=out,
        environment=env,
        portfolio_context=args.portfolio_context,
        persist_signals=not args.dry_run,
    )
    print("RUN_ID", res["run_id"])
    print("COMBINED", res["combined_zip"])
    for k, v in (res.get("individual_zips") or {}).items():
        print("JOB_ZIP", k, v)
    if store:
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
