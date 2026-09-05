from __future__ import annotations

from typing import Any
from pathlib import Path
import json
import sqlite3
from datetime import datetime, timezone

from egxbridge import __version__ as BRIDGE_VERSION
from egxbridge.analysis.common.environment import PRODUCTION, normalize_environment


ANALYSIS_SCHEMA = """
CREATE TABLE IF NOT EXISTS analysis_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    workflow_type TEXT NOT NULL,
    project_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(ticker, workflow_type)
);

CREATE TABLE IF NOT EXISTS funnel_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    run_mode TEXT,
    funnel_version TEXT,
    bridge_version TEXT,
    started_at TEXT,
    finished_at TEXT,
    status TEXT,
    manifest_json TEXT
);

CREATE TABLE IF NOT EXISTS funnel_stage_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    stage_id TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    source_file TEXT,
    content_hash TEXT,
    content_text TEXT NOT NULL,
    meta_json TEXT,
    UNIQUE(ticker, stage_id, content_hash)
);

CREATE TABLE IF NOT EXISTS funnel_key_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    key_name TEXT NOT NULL,
    value_text TEXT,
    as_of TEXT,
    source_stage TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS funnel_corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    key_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason TEXT,
    source TEXT,
    affected_downstream_stages TEXT,
    recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS explorer_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    horizon TEXT,
    generated_at TEXT NOT NULL,
    bridge_version TEXT,
    manifest_json TEXT,
    status TEXT
);

CREATE TABLE IF NOT EXISTS explorer_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    ticker TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    funnel_status TEXT,
    selection_basis TEXT,
    selection_bias_risk TEXT,
    imported_at TEXT,
    FOREIGN KEY(run_id) REFERENCES explorer_runs(id)
);

CREATE TABLE IF NOT EXISTS analysis_imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_type TEXT NOT NULL,
    ticker_or_universe TEXT,
    generated_at TEXT,
    imported_at TEXT NOT NULL,
    funnel_version TEXT,
    bridge_version TEXT,
    data_cutoff TEXT,
    market_session TEXT,
    source_file TEXT,
    content_hash TEXT,
    previous_analysis_id TEXT,
    run_mode TEXT,
    content_text TEXT NOT NULL
);
"""

V06_SCHEMA = """
CREATE TABLE IF NOT EXISTS schedule_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL UNIQUE,
    generated_at TEXT NOT NULL,
    bridge_version TEXT,
    explorer_version TEXT,
    scoring_version TEXT,
    environment TEXT,
    latest_completed_market_session TEXT,
    session_phase TEXT,
    manifest_json TEXT,
    package_dir TEXT,
    status TEXT
);

CREATE TABLE IF NOT EXISTS schedule_analysis_imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_result_id TEXT NOT NULL UNIQUE,
    analysis_type TEXT NOT NULL,
    run_id TEXT,
    generated_by TEXT DEFAULT 'CHATGPT_HANDOFF',
    imported_at TEXT NOT NULL,
    analysis_timestamp TEXT,
    latest_market_session TEXT,
    source_content_hash TEXT,
    raw_result_path TEXT,
    source_file TEXT,
    content_text TEXT NOT NULL,
    envelope_json TEXT,
    environment TEXT
);

CREATE TABLE IF NOT EXISTS signal_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT NOT NULL UNIQUE,
    run_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    analysis_type TEXT NOT NULL,
    scoring_version TEXT NOT NULL,
    package_generated_at TEXT,
    analysis_timestamp_utc TEXT,
    analysis_timestamp_cairo TEXT,
    latest_completed_market_session TEXT,
    session_phase TEXT,
    payload_json TEXT NOT NULL,
    environment TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS signal_candidate_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT,
    analysis_result_id TEXT,
    ticker TEXT NOT NULL,
    analysis_type TEXT,
    catalyst_status TEXT,
    next_session_status TEXT,
    setup_state TEXT,
    funnel_action TEXT,
    payload_json TEXT,
    imported_at TEXT,
    environment TEXT
);

CREATE TABLE IF NOT EXISTS signal_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT NOT NULL UNIQUE,
    ticker TEXT NOT NULL,
    outcome_status TEXT,
    outcome_baseline_price REAL,
    outcome_baseline_timestamp TEXT,
    outcome_baseline_type TEXT,
    next_session_return REAL,
    return_3_sessions REAL,
    return_5_sessions REAL,
    return_10_sessions REAL,
    mfe_1 REAL, mae_1 REAL,
    mfe_3 REAL, mae_3 REAL,
    mfe_5 REAL, mae_5 REAL,
    outcome_integrity_warning INTEGER DEFAULT 0,
    computed_at TEXT,
    payload_json TEXT,
    environment TEXT
);

CREATE TABLE IF NOT EXISTS user_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT,
    ticker TEXT,
    user_action TEXT,
    user_entry_price REAL,
    user_exit_price REAL,
    user_position_size TEXT,
    notes TEXT,
    recorded_at TEXT,
    environment TEXT
);

CREATE TABLE IF NOT EXISTS daily_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_date TEXT NOT NULL,
    run_id TEXT,
    payload_json TEXT NOT NULL,
    environment TEXT,
    created_at TEXT,
    UNIQUE(decision_date, environment, run_id)
);

CREATE TABLE IF NOT EXISTS calibration_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_at TEXT,
    grouping TEXT,
    payload_json TEXT,
    calibration_status TEXT,
    n INTEGER,
    environment TEXT
);
"""

V061_SCHEMA = """
CREATE TABLE IF NOT EXISTS canonical_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_signal_id TEXT NOT NULL UNIQUE,
    ticker TEXT NOT NULL,
    environment TEXT NOT NULL,
    market_session_basis TEXT,
    signal_timestamp TEXT,
    signal_origin TEXT NOT NULL,
    scoring_version TEXT NOT NULL,
    explorer_run_id TEXT,
    candidate_rank INTEGER,
    candidate_lane TEXT,
    FORWARD_SETUP_QUALITY TEXT,
    MOVE_ALREADY_REALIZED TEXT,
    candidate_score_calibrated REAL,
    price_at_signal REAL,
    price_observation_type TEXT,
    session_phase TEXT,
    parent_signal_id TEXT,
    signal_family_id TEXT,
    origin_snapshot_id TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_observation_id TEXT NOT NULL UNIQUE,
    canonical_signal_id TEXT NOT NULL,
    analysis_type TEXT NOT NULL,
    analysis_timestamp TEXT,
    schedule_run_id TEXT,
    explorer_run_id TEXT,
    ticker TEXT NOT NULL,
    generated_by TEXT,
    chatgpt_status TEXT,
    catalyst_status TEXT,
    setup_state TEXT,
    funnel_action TEXT,
    next_session_status TEXT,
    imported_at TEXT,
    payload_json TEXT,
    environment TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS canonical_signal_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_signal_id TEXT NOT NULL UNIQUE,
    ticker TEXT NOT NULL,
    outcome_status TEXT,
    outcome_baseline_price REAL,
    outcome_baseline_timestamp TEXT,
    outcome_baseline_type TEXT,
    next_session_return REAL,
    return_3_sessions REAL,
    return_5_sessions REAL,
    return_10_sessions REAL,
    mfe_1 REAL, mae_1 REAL,
    mfe_3 REAL, mae_3 REAL,
    mfe_5 REAL, mae_5 REAL,
    outcome_integrity_warning INTEGER DEFAULT 0,
    computed_at TEXT,
    payload_json TEXT,
    environment TEXT
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AnalysisStore:
    """Minimal SQLite persistence for Funnel/Explorer (does not duplicate market tables)."""

    def __init__(self, path: str | Path, environment: str = PRODUCTION):
        self.path = Path(path)
        self.environment = normalize_environment(environment)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(ANALYSIS_SCHEMA)
        self._conn.executescript(V06_SCHEMA)
        self._conn.executescript(V061_SCHEMA)
        self._ensure_environment_columns()
        self._ensure_v062_columns()
        self._ensure_v070_tables()
        self._conn.commit()

    VALIDATION_TABLES = {
        "forward_test_runs", "forward_signal_snapshots", "forward_signal_classifications",
        "universe_snapshots", "universe_snapshot_members", "universe_member_outcomes",
        "rule_definitions", "rule_change_proposals", "later_event_reviews",
    }

    def _ensure_v070_tables(self):
        # Payloads are versioned JSON; searchable identities remain indexed in SQLite.
        for table in self.VALIDATION_TABLES:
            self._conn.execute(f"""CREATE TABLE IF NOT EXISTS {table} (
                record_id TEXT NOT NULL, environment TEXT NOT NULL,
                canonical_signal_id TEXT, ticker TEXT, created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL, PRIMARY KEY (environment, record_id))""")
            self._conn.execute(f"CREATE INDEX IF NOT EXISTS ix_{table}_signal ON {table}(environment, canonical_signal_id)")
            if table != "universe_member_outcomes":
                for operation in ("UPDATE", "DELETE"):
                    self._conn.execute(f"""CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation}
                        BEFORE {operation} ON {table} BEGIN
                        SELECT RAISE(ABORT, 'immutable validation evidence'); END""")

    def append_validation_record(self, table: str, record_id: str, payload: dict[str, Any]) -> bool:
        if table not in self.VALIDATION_TABLES or table == "universe_member_outcomes":
            raise ValueError("Not an immutable validation table")
        if payload.get("environment", self.environment) != self.environment:
            raise ValueError("Validation environment mismatch")
        cur = self._conn.execute(
            f"INSERT OR IGNORE INTO {table} VALUES (?,?,?,?,?,?)",
            (record_id, self.environment, payload.get("canonical_signal_id"), payload.get("ticker"),
             _now(), json.dumps({**payload, "environment": self.environment}, default=str, allow_nan=False)),
        )
        self._conn.commit()
        return cur.rowcount == 1

    def validation_records(self, table: str, *, canonical_signal_id: str | None = None) -> list[dict[str, Any]]:
        if table not in self.VALIDATION_TABLES:
            raise ValueError("Unknown validation table")
        query = f"SELECT record_id, payload_json FROM {table} WHERE environment=?"
        args = [self.environment]
        if canonical_signal_id is not None:
            query += " AND canonical_signal_id=?"
            args.append(canonical_signal_id)
        query += " ORDER BY created_at, record_id"
        return [{**json.loads(r["payload_json"]), "record_id": r["record_id"]}
                for r in self._conn.execute(query, args)]

    def upsert_universe_outcome(self, member_id: str, payload: dict[str, Any]):
        self._conn.execute(
            """INSERT INTO universe_member_outcomes VALUES (?,?,?,?,?,?)
               ON CONFLICT(environment, record_id) DO UPDATE SET payload_json=excluded.payload_json""",
            (member_id, self.environment, None, payload.get("ticker"), _now(), json.dumps(payload, allow_nan=False)),
        )
        self._conn.commit()

    def _ensure_environment_columns(self):
        tables = (
            "analysis_projects", "funnel_runs", "funnel_stage_results",
            "funnel_key_values", "funnel_corrections", "explorer_runs",
            "explorer_candidates", "analysis_imports",
            "schedule_runs", "schedule_analysis_imports", "signal_snapshots",
            "signal_candidate_states", "signal_outcomes", "user_actions",
            "daily_decisions", "calibration_summaries",
            "canonical_signals", "analysis_observations", "canonical_signal_outcomes",
        )
        for table in tables:
            cols = {r[1] for r in self._conn.execute(f"PRAGMA table_info({table})")}
            if "environment" not in cols:
                self._conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN environment TEXT DEFAULT '{PRODUCTION}'"
                )

    def _ensure_v062_columns(self):
        """Additive only. Existing production DBs keep historical rows intact."""
        extras = {
            "canonical_signals": {
                "market_state_fingerprint": "TEXT",
                "first_explorer_run_id": "TEXT",
                "latest_seen_explorer_run_id": "TEXT",
            },
            "analysis_observations": {
                "linkage_method": "TEXT",
                "import_status": "TEXT",
                "result_envelope_version": "TEXT",
            },
        }
        for table, cols_ddl in extras.items():
            existing = {r[1] for r in self._conn.execute(f"PRAGMA table_info({table})")}
            for col, ddl in cols_ddl.items():
                if col not in existing:
                    self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")

    def close(self):
        self._conn.close()

    def upsert_project(self, ticker: str, workflow_type: str, project: dict[str, Any]):
        now = _now()
        self._conn.execute(
            """INSERT INTO analysis_projects(ticker, workflow_type, project_json, created_at, updated_at, environment)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(ticker, workflow_type) DO UPDATE SET
                 project_json=excluded.project_json, updated_at=excluded.updated_at,
                 environment=excluded.environment
            """,
            (ticker.upper(), workflow_type, json.dumps(project, default=str), now, now, self.environment),
        )
        self._conn.commit()

    def get_project(self, ticker: str, workflow_type: str = "funnel") -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT project_json FROM analysis_projects WHERE ticker=? AND workflow_type=? AND environment=?",
            (ticker.upper(), workflow_type, self.environment),
        ).fetchone()
        return json.loads(row["project_json"]) if row else None

    def insert_stage_result(self, ticker: str, stage_id: str, content_text: str, *,
                            source_file: str | None = None, meta: dict | None = None) -> str:
        from egxbridge.analysis.common.models import content_hash
        h = content_hash(content_text)
        now = _now()
        self._conn.execute(
            """INSERT OR IGNORE INTO funnel_stage_results(
                ticker, stage_id, imported_at, source_file, content_hash, content_text, meta_json, environment
            ) VALUES (?,?,?,?,?,?,?,?)""",
            (ticker.upper(), stage_id, now, source_file, h, content_text, json.dumps(meta or {}), self.environment),
        )
        self._conn.commit()
        return h

    def get_stage_result(self, ticker: str, stage_id: str) -> dict[str, Any] | None:
        """Latest imported result for a stage (by import time)."""
        row = self._conn.execute(
            """SELECT stage_id, imported_at, source_file, content_hash, content_text, meta_json
               FROM funnel_stage_results
               WHERE ticker=? AND stage_id=? AND environment=?
               ORDER BY imported_at DESC LIMIT 1""",
            (ticker.upper(), str(stage_id), self.environment),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["meta"] = json.loads(d.pop("meta_json") or "{}")
        return d

    def list_stage_results(self, ticker: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """SELECT stage_id, imported_at, source_file, content_hash, content_text, meta_json
               FROM funnel_stage_results WHERE ticker=? AND environment=? ORDER BY imported_at""",
            (ticker.upper(), self.environment),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["meta"] = json.loads(d.pop("meta_json") or "{}")
            out.append(d)
        return out

    def set_key_value(self, ticker: str, key_name: str, value_text: str | None, *,
                      as_of: str | None = None, source_stage: str | None = None,
                      old_value: str | None = None, reason: str = "", source: str = "",
                      affected: list[str] | None = None):
        now = _now()
        # append correction if changing
        prev = self.get_key_value(ticker, key_name)
        if prev is not None and prev != value_text:
            self._conn.execute(
                """INSERT INTO funnel_corrections(
                    ticker, key_name, old_value, new_value, reason, source,
                    affected_downstream_stages, recorded_at, environment
                ) VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    ticker.upper(), key_name, prev if old_value is None else old_value,
                    value_text, reason, source, json.dumps(affected or []), now, self.environment,
                ),
            )
        elif old_value is not None and old_value != value_text:
            self._conn.execute(
                """INSERT INTO funnel_corrections(
                    ticker, key_name, old_value, new_value, reason, source,
                    affected_downstream_stages, recorded_at, environment
                ) VALUES (?,?,?,?,?,?,?,?,?)""",
                (ticker.upper(), key_name, old_value, value_text, reason, source,
                 json.dumps(affected or []), now, self.environment),
            )
        # upsert current
        existing = self._conn.execute(
            "SELECT id FROM funnel_key_values WHERE ticker=? AND key_name=? AND environment=?",
            (ticker.upper(), key_name, self.environment),
        ).fetchone()
        if existing:
            self._conn.execute(
                """UPDATE funnel_key_values SET value_text=?, as_of=?, source_stage=?, updated_at=?
                   WHERE ticker=? AND key_name=? AND environment=?""",
                (value_text, as_of, source_stage, now, ticker.upper(), key_name, self.environment),
            )
        else:
            self._conn.execute(
                """INSERT INTO funnel_key_values(ticker, key_name, value_text, as_of, source_stage, updated_at, environment)
                   VALUES (?,?,?,?,?,?,?)""",
                (ticker.upper(), key_name, value_text, as_of, source_stage, now, self.environment),
            )
        self._conn.commit()

    def get_key_value(self, ticker: str, key_name: str) -> str | None:
        row = self._conn.execute(
            "SELECT value_text FROM funnel_key_values WHERE ticker=? AND key_name=? AND environment=?",
            (ticker.upper(), key_name, self.environment),
        ).fetchone()
        return row["value_text"] if row else None

    def all_key_values(self, ticker: str) -> dict[str, str | None]:
        rows = self._conn.execute(
            "SELECT key_name, value_text FROM funnel_key_values WHERE ticker=? AND environment=?",
            (ticker.upper(), self.environment),
        ).fetchall()
        return {r["key_name"]: r["value_text"] for r in rows}

    def list_corrections(self, ticker: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM funnel_corrections WHERE ticker=? AND environment=? ORDER BY id",
            (ticker.upper(), self.environment),
        ).fetchall()
        return [dict(r) for r in rows]

    def record_import(self, provenance: dict[str, Any], content_text: str) -> int:
        cur = self._conn.execute(
            """INSERT INTO analysis_imports(
                analysis_type, ticker_or_universe, generated_at, imported_at, funnel_version,
                bridge_version, data_cutoff, market_session, source_file, content_hash,
                previous_analysis_id, run_mode, content_text, environment
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                provenance.get("analysis_type"), provenance.get("ticker_or_universe"),
                provenance.get("generated_at"), provenance.get("imported_at") or _now(),
                provenance.get("funnel_version"), provenance.get("bridge_version") or BRIDGE_VERSION,
                provenance.get("data_cutoff"), provenance.get("market_session"),
                provenance.get("source_file"), provenance.get("content_hash"),
                provenance.get("previous_analysis_id"), provenance.get("run_mode"),
                content_text, self.environment,
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def insert_explorer_run(self, horizon: str, manifest: dict[str, Any], status: str = "PREPARED") -> int:
        cur = self._conn.execute(
            """INSERT INTO explorer_runs(horizon, generated_at, bridge_version, manifest_json, status, environment)
               VALUES (?,?,?,?,?,?)""",
            (horizon, _now(), BRIDGE_VERSION, json.dumps(manifest, default=str), status, self.environment),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def insert_explorer_candidate(self, run_id: int, ticker: str, payload: dict[str, Any]):
        self._conn.execute(
            """INSERT INTO explorer_candidates(
                run_id, ticker, payload_json, funnel_status, selection_basis, selection_bias_risk, imported_at, environment
            ) VALUES (?,?,?,?,?,?,?,?)""",
            (
                run_id, ticker.upper(), json.dumps(payload, default=str),
                payload.get("funnel_status"), payload.get("selection_basis"),
                payload.get("selection_bias_risk"), _now(), self.environment,
            ),
        )
        self._conn.commit()

    def list_funnel_tickers(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT ticker FROM analysis_projects WHERE workflow_type='funnel' AND environment=?",
            (self.environment,),
        ).fetchall()
        return [r["ticker"] for r in rows]

    def insert_schedule_run(self, run_id: str, manifest: dict[str, Any], *, package_dir: str | None = None, status: str = "PREPARED") -> str:
        self._conn.execute(
            """INSERT OR IGNORE INTO schedule_runs(
                run_id, generated_at, bridge_version, explorer_version, scoring_version,
                environment, latest_completed_market_session, session_phase, manifest_json,
                package_dir, status
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                run_id, manifest.get("generated_at") or _now(),
                manifest.get("bridge_version") or BRIDGE_VERSION,
                manifest.get("explorer_version"),
                manifest.get("scoring_version") or "0.5.1",
                self.environment,
                manifest.get("latest_completed_market_session"),
                manifest.get("session_phase"),
                json.dumps(manifest, default=str),
                package_dir, status,
            ),
        )
        self._conn.commit()
        return run_id

    def latest_schedule_run(self) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM schedule_runs WHERE environment=? ORDER BY id DESC LIMIT 1",
            (self.environment,),
        ).fetchone()
        return dict(row) if row else None

    def insert_signal_snapshot(self, snapshot: dict[str, Any]) -> tuple[str, bool]:
        """Append-only. Returns (snapshot_id, inserted). Never overwrites payload."""
        sid = snapshot["snapshot_id"]
        existing = self._conn.execute(
            "SELECT snapshot_id, payload_json FROM signal_snapshots WHERE snapshot_id=?",
            (sid,),
        ).fetchone()
        if existing:
            return sid, False
        self._conn.execute(
            """INSERT INTO signal_snapshots(
                snapshot_id, run_id, ticker, analysis_type, scoring_version,
                package_generated_at, analysis_timestamp_utc, analysis_timestamp_cairo,
                latest_completed_market_session, session_phase, payload_json,
                environment, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                sid, snapshot.get("run_id"), str(snapshot.get("ticker") or "").upper(),
                snapshot.get("analysis_type"), snapshot.get("scoring_version") or "0.5.1",
                snapshot.get("package_generated_at"), snapshot.get("analysis_timestamp_utc"),
                snapshot.get("analysis_timestamp_cairo"),
                snapshot.get("latest_completed_market_session"),
                snapshot.get("session_phase"),
                json.dumps(snapshot, default=str),
                self.environment, _now(),
            ),
        )
        self._conn.commit()
        return sid, True

    def get_signal_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM signal_snapshots WHERE snapshot_id=?", (snapshot_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["payload"] = json.loads(d.get("payload_json") or "{}")
        return d

    def list_signal_snapshots(self, *, ticker: str | None = None, analysis_type: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
        q = "SELECT * FROM signal_snapshots WHERE environment=?"
        args: list[Any] = [self.environment]
        if ticker:
            q += " AND ticker=?"
            args.append(ticker.upper())
        if analysis_type:
            q += " AND analysis_type=?"
            args.append(analysis_type)
        q += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        rows = self._conn.execute(q, args).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["payload"] = json.loads(d.get("payload_json") or "{}")
            out.append(d)
        return out

    def insert_schedule_import(self, rec: dict[str, Any]) -> str:
        self._conn.execute(
            """INSERT OR IGNORE INTO schedule_analysis_imports(
                analysis_result_id, analysis_type, run_id, generated_by, imported_at,
                analysis_timestamp, latest_market_session, source_content_hash,
                raw_result_path, source_file, content_text, envelope_json, environment
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                rec["analysis_result_id"], rec.get("analysis_type"), rec.get("run_id"),
                rec.get("generated_by") or "CHATGPT_HANDOFF", rec.get("imported_at") or _now(),
                rec.get("analysis_timestamp"), rec.get("latest_market_session"),
                rec.get("source_content_hash"), rec.get("raw_result_path"),
                rec.get("source_file"), rec.get("content_text") or "",
                json.dumps(rec.get("envelope"), default=str) if rec.get("envelope") is not None else None,
                self.environment,
            ),
        )
        self._conn.commit()
        return rec["analysis_result_id"]

    def latest_schedule_import(self, analysis_type: str | None = None) -> dict[str, Any] | None:
        if analysis_type:
            row = self._conn.execute(
                """SELECT * FROM schedule_analysis_imports
                   WHERE environment=? AND analysis_type=? ORDER BY id DESC LIMIT 1""",
                (self.environment, analysis_type),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT * FROM schedule_analysis_imports WHERE environment=? ORDER BY id DESC LIMIT 1",
                (self.environment,),
            ).fetchone()
        if not row:
            return None
        d = dict(row)
        if d.get("envelope_json"):
            try:
                d["envelope"] = json.loads(d["envelope_json"])
            except Exception:
                d["envelope"] = None
        return d

    def insert_candidate_state(self, rec: dict[str, Any]) -> None:
        self._conn.execute(
            """INSERT INTO signal_candidate_states(
                snapshot_id, analysis_result_id, ticker, analysis_type, catalyst_status,
                next_session_status, setup_state, funnel_action, payload_json,
                imported_at, environment
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                rec.get("snapshot_id"), rec.get("analysis_result_id"),
                str(rec.get("ticker") or "").upper(), rec.get("analysis_type"),
                rec.get("catalyst_status"), rec.get("next_session_status"),
                rec.get("setup_state"), rec.get("funnel_action"),
                json.dumps(rec.get("payload") or rec, default=str),
                rec.get("imported_at") or _now(), self.environment,
            ),
        )
        self._conn.commit()

    def upsert_signal_outcome(self, rec: dict[str, Any]) -> None:
        """Outcomes may be refreshed as more sessions arrive. Snapshot payload is never touched."""
        payload = json.dumps(rec, default=str)
        existing = self._conn.execute(
            "SELECT id FROM signal_outcomes WHERE snapshot_id=?", (rec["snapshot_id"],),
        ).fetchone()
        fields = (
            rec.get("ticker"), rec.get("outcome_status"),
            rec.get("outcome_baseline_price"), rec.get("outcome_baseline_timestamp"),
            rec.get("outcome_baseline_type"), rec.get("next_session_return"),
            rec.get("return_3_sessions"), rec.get("return_5_sessions"), rec.get("return_10_sessions"),
            rec.get("mfe_1"), rec.get("mae_1"), rec.get("mfe_3"), rec.get("mae_3"),
            rec.get("mfe_5"), rec.get("mae_5"),
            1 if rec.get("outcome_integrity_warning") else 0,
            rec.get("computed_at") or _now(), payload, self.environment, rec["snapshot_id"],
        )
        if existing:
            self._conn.execute(
                """UPDATE signal_outcomes SET
                    ticker=?, outcome_status=?, outcome_baseline_price=?, outcome_baseline_timestamp=?,
                    outcome_baseline_type=?, next_session_return=?, return_3_sessions=?,
                    return_5_sessions=?, return_10_sessions=?, mfe_1=?, mae_1=?, mfe_3=?, mae_3=?,
                    mfe_5=?, mae_5=?, outcome_integrity_warning=?, computed_at=?, payload_json=?,
                    environment=?
                   WHERE snapshot_id=?""",
                fields,
            )
        else:
            self._conn.execute(
                """INSERT INTO signal_outcomes(
                    ticker, outcome_status, outcome_baseline_price, outcome_baseline_timestamp,
                    outcome_baseline_type, next_session_return, return_3_sessions, return_5_sessions,
                    return_10_sessions, mfe_1, mae_1, mfe_3, mae_3, mfe_5, mae_5,
                    outcome_integrity_warning, computed_at, payload_json, environment, snapshot_id
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                fields,
            )
        self._conn.commit()

    def list_signal_outcomes(self, *, ticker: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
        q = "SELECT * FROM signal_outcomes WHERE environment=?"
        args: list[Any] = [self.environment]
        if ticker:
            q += " AND ticker=?"
            args.append(ticker.upper())
        q += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        return [dict(r) for r in self._conn.execute(q, args).fetchall()]

    def pending_outcome_snapshots(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """SELECT s.* FROM signal_snapshots s
               LEFT JOIN signal_outcomes o ON o.snapshot_id = s.snapshot_id
               WHERE s.environment=?
                 AND (o.snapshot_id IS NULL OR o.outcome_status IN ('PENDING','PARTIAL'))
               ORDER BY s.id""",
            (self.environment,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["payload"] = json.loads(d.get("payload_json") or "{}")
            out.append(d)
        return out

    def insert_user_action(self, rec: dict[str, Any]) -> None:
        self._conn.execute(
            """INSERT INTO user_actions(
                snapshot_id, ticker, user_action, user_entry_price, user_exit_price,
                user_position_size, notes, recorded_at, environment
            ) VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                rec.get("snapshot_id"), str(rec.get("ticker") or "").upper(),
                rec.get("user_action"), rec.get("user_entry_price"),
                rec.get("user_exit_price"), rec.get("user_position_size"),
                rec.get("notes"), rec.get("recorded_at") or _now(), self.environment,
            ),
        )
        self._conn.commit()

    def upsert_daily_decision(self, decision_date: str, run_id: str, payload: dict[str, Any]) -> None:
        now = _now()
        self._conn.execute(
            """INSERT INTO daily_decisions(decision_date, run_id, payload_json, environment, created_at)
               VALUES (?,?,?,?,?)
               ON CONFLICT(decision_date, environment, run_id) DO UPDATE SET payload_json=excluded.payload_json""",
            (decision_date, run_id, json.dumps(payload, default=str), self.environment, now),
        )
        self._conn.commit()

    def _touch_canonical_provenance(self, canonical_signal_id: str, explorer_run_id: str | None) -> None:
        if not explorer_run_id:
            return
        self._conn.execute(
            """UPDATE canonical_signals SET latest_seen_explorer_run_id=?
               WHERE canonical_signal_id=?""",
            (explorer_run_id, canonical_signal_id),
        )
        self._conn.commit()

    def find_canonical_by_market_state(
        self,
        *,
        ticker: str,
        market_session_basis: str | None,
        scoring_version: str | None,
        market_state_fingerprint: str | None,
        signal_origin: str | None = None,
    ) -> dict[str, Any] | None:
        if not market_state_fingerprint:
            return None
        q = """SELECT * FROM canonical_signals
               WHERE environment=? AND ticker=? AND scoring_version=?
                 AND ifnull(market_session_basis,'')=?
                 AND market_state_fingerprint=?"""
        args: list[Any] = [
            self.environment, str(ticker or "").upper(), scoring_version or "0.5.1",
            market_session_basis or "", market_state_fingerprint,
        ]
        if signal_origin:
            q += " AND signal_origin=?"
            args.append(signal_origin)
        q += " ORDER BY id ASC LIMIT 1"
        row = self._conn.execute(q, args).fetchone()
        if not row:
            return None
        d = dict(row)
        d["payload"] = json.loads(d.get("payload_json") or "{}")
        return d

    def insert_canonical_signal(self, rec: dict[str, Any]) -> tuple[str, bool]:
        """Append-only market-state payload. Provenance latest_seen_explorer_run_id may update."""
        cid = rec["canonical_signal_id"]
        existing = self._conn.execute(
            "SELECT canonical_signal_id FROM canonical_signals WHERE canonical_signal_id=?",
            (cid,),
        ).fetchone()
        if existing:
            self._touch_canonical_provenance(cid, rec.get("latest_seen_explorer_run_id") or rec.get("explorer_run_id"))
            return cid, False
        by_fp = self.find_canonical_by_market_state(
            ticker=str(rec.get("ticker") or ""),
            market_session_basis=rec.get("market_session_basis"),
            scoring_version=rec.get("scoring_version"),
            market_state_fingerprint=rec.get("market_state_fingerprint"),
            signal_origin=rec.get("signal_origin"),
        )
        if by_fp:
            found_id = by_fp["canonical_signal_id"]
            self._touch_canonical_provenance(
                found_id, rec.get("latest_seen_explorer_run_id") or rec.get("explorer_run_id"),
            )
            return found_id, False
        xr = rec.get("explorer_run_id")
        self._conn.execute(
            """INSERT INTO canonical_signals(
                canonical_signal_id, ticker, environment, market_session_basis, signal_timestamp,
                signal_origin, scoring_version, explorer_run_id, candidate_rank, candidate_lane,
                FORWARD_SETUP_QUALITY, MOVE_ALREADY_REALIZED, candidate_score_calibrated,
                price_at_signal, price_observation_type, session_phase, parent_signal_id,
                signal_family_id, origin_snapshot_id, payload_json, created_at,
                market_state_fingerprint, first_explorer_run_id, latest_seen_explorer_run_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                cid, str(rec.get("ticker") or "").upper(), rec.get("environment") or self.environment,
                rec.get("market_session_basis"), rec.get("signal_timestamp"),
                rec.get("signal_origin") or "EXPLORER", rec.get("scoring_version") or "0.5.1",
                xr, rec.get("candidate_rank"), rec.get("candidate_lane"),
                rec.get("FORWARD_SETUP_QUALITY"), rec.get("MOVE_ALREADY_REALIZED"),
                rec.get("candidate_score_calibrated"), rec.get("price_at_signal"),
                rec.get("price_observation_type"), rec.get("session_phase"),
                rec.get("parent_signal_id"), rec.get("signal_family_id"),
                rec.get("origin_snapshot_id"), json.dumps(rec, default=str), _now(),
                rec.get("market_state_fingerprint"),
                rec.get("first_explorer_run_id") or xr,
                rec.get("latest_seen_explorer_run_id") or xr,
            ),
        )
        self._conn.commit()
        return cid, True

    def get_canonical_signal(self, canonical_signal_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM canonical_signals WHERE canonical_signal_id=?",
            (canonical_signal_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["payload"] = json.loads(d.get("payload_json") or "{}")
        return d

    def list_canonical_signals(self, *, ticker: str | None = None, limit: int = 2000) -> list[dict[str, Any]]:
        q = "SELECT * FROM canonical_signals WHERE environment=?"
        args: list[Any] = [self.environment]
        if ticker:
            q += " AND ticker=?"
            args.append(ticker.upper())
        q += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        out = []
        for r in self._conn.execute(q, args).fetchall():
            d = dict(r)
            d["payload"] = json.loads(d.get("payload_json") or "{}")
            out.append(d)
        return out

    def insert_analysis_observation(self, rec: dict[str, Any]) -> tuple[str, bool]:
        oid = rec["analysis_observation_id"]
        existing = self._conn.execute(
            "SELECT analysis_observation_id FROM analysis_observations WHERE analysis_observation_id=?",
            (oid,),
        ).fetchone()
        if existing:
            return oid, False
        self._conn.execute(
            """INSERT INTO analysis_observations(
                analysis_observation_id, canonical_signal_id, analysis_type, analysis_timestamp,
                schedule_run_id, explorer_run_id, ticker, generated_by, chatgpt_status,
                catalyst_status, setup_state, funnel_action, next_session_status, imported_at,
                payload_json, environment, created_at,
                linkage_method, import_status, result_envelope_version
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                oid, rec.get("canonical_signal_id"), rec.get("analysis_type"),
                rec.get("analysis_timestamp"), rec.get("schedule_run_id"), rec.get("explorer_run_id"),
                str(rec.get("ticker") or "").upper(), rec.get("generated_by") or "LOCAL",
                rec.get("chatgpt_status"), rec.get("catalyst_status"), rec.get("setup_state"),
                rec.get("funnel_action"), rec.get("next_session_status"), rec.get("imported_at"),
                json.dumps(rec, default=str), rec.get("environment") or self.environment, _now(),
                rec.get("linkage_method"), rec.get("import_status") or "GENERATED",
                rec.get("result_envelope_version"),
            ),
        )
        self._conn.commit()
        return oid, True

    def update_analysis_observation_import(self, rec: dict[str, Any]) -> str:
        """Fill ChatGPT/import fields on an observation. Does not rewrite canonical signals."""
        oid = rec.get("analysis_observation_id")
        if oid:
            existing = self._conn.execute(
                "SELECT analysis_observation_id FROM analysis_observations WHERE analysis_observation_id=?",
                (oid,),
            ).fetchone()
            if existing:
                self._conn.execute(
                    """UPDATE analysis_observations SET
                        chatgpt_status=?, catalyst_status=?, setup_state=?, funnel_action=?,
                        next_session_status=?, imported_at=?, payload_json=?,
                        linkage_method=?, import_status=?, result_envelope_version=?
                       WHERE analysis_observation_id=?""",
                    (
                        rec.get("chatgpt_status"), rec.get("catalyst_status"), rec.get("setup_state"),
                        rec.get("funnel_action"), rec.get("next_session_status"),
                        rec.get("imported_at") or _now(), json.dumps(rec, default=str),
                        rec.get("linkage_method"), rec.get("import_status") or "IMPORTED",
                        rec.get("result_envelope_version"), oid,
                    ),
                )
                self._conn.commit()
                return oid
        oid2, _ = self.insert_analysis_observation(rec)
        return oid2

    def list_analysis_observations(
        self, *, canonical_signal_id: str | None = None, ticker: str | None = None, limit: int = 5000,
    ) -> list[dict[str, Any]]:
        q = "SELECT * FROM analysis_observations WHERE environment=?"
        args: list[Any] = [self.environment]
        if canonical_signal_id:
            q += " AND canonical_signal_id=?"
            args.append(canonical_signal_id)
        if ticker:
            q += " AND ticker=?"
            args.append(ticker.upper())
        q += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        out = []
        for r in self._conn.execute(q, args).fetchall():
            d = dict(r)
            d["payload"] = json.loads(d.get("payload_json") or "{}")
            out.append(d)
        return out

    def upsert_canonical_outcome(self, rec: dict[str, Any]) -> None:
        """Outcomes attach to canonical_signal_id. Snapshot/canonical payloads are never touched."""
        payload = json.dumps(rec, default=str)
        cid = rec["canonical_signal_id"]
        existing = self._conn.execute(
            "SELECT id FROM canonical_signal_outcomes WHERE canonical_signal_id=?", (cid,),
        ).fetchone()
        fields = (
            rec.get("ticker"), rec.get("outcome_status"),
            rec.get("outcome_baseline_price"), rec.get("outcome_baseline_timestamp"),
            rec.get("outcome_baseline_type"), rec.get("next_session_return"),
            rec.get("return_3_sessions"), rec.get("return_5_sessions"), rec.get("return_10_sessions"),
            rec.get("mfe_1"), rec.get("mae_1"), rec.get("mfe_3"), rec.get("mae_3"),
            rec.get("mfe_5"), rec.get("mae_5"),
            1 if rec.get("outcome_integrity_warning") else 0,
            rec.get("computed_at") or _now(), payload, rec.get("environment") or self.environment, cid,
        )
        if existing:
            self._conn.execute(
                """UPDATE canonical_signal_outcomes SET
                    ticker=?, outcome_status=?, outcome_baseline_price=?, outcome_baseline_timestamp=?,
                    outcome_baseline_type=?, next_session_return=?, return_3_sessions=?,
                    return_5_sessions=?, return_10_sessions=?, mfe_1=?, mae_1=?, mfe_3=?, mae_3=?,
                    mfe_5=?, mae_5=?, outcome_integrity_warning=?, computed_at=?, payload_json=?,
                    environment=?
                   WHERE canonical_signal_id=?""",
                fields,
            )
        else:
            self._conn.execute(
                """INSERT INTO canonical_signal_outcomes(
                    ticker, outcome_status, outcome_baseline_price, outcome_baseline_timestamp,
                    outcome_baseline_type, next_session_return, return_3_sessions, return_5_sessions,
                    return_10_sessions, mfe_1, mae_1, mfe_3, mae_3, mfe_5, mae_5,
                    outcome_integrity_warning, computed_at, payload_json, environment, canonical_signal_id
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                fields,
            )
        self._conn.commit()

    def list_canonical_outcomes(self, *, ticker: str | None = None, limit: int = 2000) -> list[dict[str, Any]]:
        q = "SELECT * FROM canonical_signal_outcomes WHERE environment=?"
        args: list[Any] = [self.environment]
        if ticker:
            q += " AND ticker=?"
            args.append(ticker.upper())
        q += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        return [dict(r) for r in self._conn.execute(q, args).fetchall()]

    def pending_canonical_signals(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """SELECT s.* FROM canonical_signals s
               LEFT JOIN canonical_signal_outcomes o ON o.canonical_signal_id = s.canonical_signal_id
               WHERE s.environment=?
                 AND (json_extract(o.payload_json, '$.maturity_20') IS NULL
                      OR json_extract(o.payload_json, '$.maturity_20') != 'MATURE')
               ORDER BY s.id""",
            (self.environment,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["payload"] = json.loads(d.get("payload_json") or "{}")
            out.append(d)
        return out

    def insert_calibration_summary(self, grouping: str, payload: dict[str, Any], *, n: int, status: str) -> None:
        self._conn.execute(
            """INSERT INTO calibration_summaries(generated_at, grouping, payload_json, calibration_status, n, environment)
               VALUES (?,?,?,?,?,?)""",
            (_now(), grouping, json.dumps(payload, default=str), status, n, self.environment),
        )
        self._conn.commit()
