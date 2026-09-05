#!/usr/bin/env python3
"""Update point-in-time signal outcomes from future trading sessions. No score retune."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import json

HERE = Path(__file__).resolve().parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from egxbridge.analysis.common.environment import PRODUCTION, normalize_environment, analysis_db_path_for
from egxbridge.analysis.common.persistence import AnalysisStore
from egxbridge.analysis.schedule.outcomes import update_outcomes_for_store
from egxbridge.config import Settings
from egxbridge.db import Database


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Compute outcomes for Explorer/schedule snapshots")
    p.add_argument("--pending-only", action="store_true", default=True)
    p.add_argument("--all", action="store_true", help="Include snapshots that already have outcomes")
    p.add_argument("--through-session", default="", help="YYYY-MM-DD inclusive cutoff")
    p.add_argument("--environment", default=PRODUCTION)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--horizons", default="1,2,5,10,20")
    p.add_argument("--forward-validation-only", action="store_true")
    args = p.parse_args(argv)

    env = normalize_environment(args.environment)
    store = AnalysisStore(analysis_db_path_for(env), environment=env)
    settings = Settings.load(HERE / "config.json")
    db = Database(settings.db_path(HERE))
    res = update_outcomes_for_store(
        store, db,
        pending_only=not args.all,
        through_session=args.through_session or None,
        dry_run=args.dry_run,
        horizons=tuple(int(h) for h in args.horizons.split(",")),
        forward_validation_only=args.forward_validation_only,
    )
    print(json.dumps(res, indent=2, default=str))
    store.close()
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
