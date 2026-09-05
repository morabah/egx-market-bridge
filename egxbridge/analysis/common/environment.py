"""Analysis environment isolation — production vs acceptance vs unit tests."""
from __future__ import annotations

from pathlib import Path

PRODUCTION = "PRODUCTION"
ACCEPTANCE_TEST = "ACCEPTANCE_TEST"
UNIT_TEST = "UNIT_TEST"

ENVIRONMENTS = {PRODUCTION, ACCEPTANCE_TEST, UNIT_TEST}

HERE = Path(__file__).resolve().parents[3]


def normalize_environment(env: str | None) -> str:
    v = (env or PRODUCTION).strip().upper()
    if v not in ENVIRONMENTS:
        raise ValueError(f"Invalid analysis environment: {env}")
    return v


def workspace_root_for(environment: str | None) -> Path:
    env = normalize_environment(environment)
    if env == ACCEPTANCE_TEST:
        return HERE / "workspace" / "acceptance" / "funnels"
    if env == UNIT_TEST:
        return HERE / "workspace" / "unit_test" / "funnels"
    return HERE / "workspace" / "funnels"


def analysis_db_path_for(environment: str | None) -> Path:
    env = normalize_environment(environment)
    if env == ACCEPTANCE_TEST:
        return HERE / "output" / "acceptance.sqlite"
    if env == UNIT_TEST:
        return HERE / "output" / "unit_test_analysis.sqlite"
    return HERE / "output" / "analysis.sqlite"
