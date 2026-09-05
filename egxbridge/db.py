from __future__ import annotations

from pathlib import Path
from typing import Any
import sqlite3
import json
from datetime import datetime, timezone


SCHEMA = """
CREATE TABLE IF NOT EXISTS symbols (
    canonical TEXT PRIMARY KEY,
    name TEXT,
    aliases_json TEXT,
    sector TEXT,
    active INTEGER DEFAULT 1,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    provider TEXT NOT NULL,
    last REAL,
    open REAL,
    high REAL,
    low REAL,
    prev_close REAL,
    change_pct REAL,
    volume REAL,
    bid REAL,
    ask REAL,
    provider_timestamp TEXT,
    capture_timestamp TEXT NOT NULL,
    freshness_class TEXT,
    provider_mode TEXT,
    raw_reference TEXT,
    UNIQUE(symbol, provider, capture_timestamp)
);

CREATE TABLE IF NOT EXISTS candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    provider TEXT NOT NULL,
    capture_timestamp TEXT NOT NULL,
    freshness_class TEXT,
    provider_mode TEXT,
    semantics_json TEXT,
    UNIQUE(symbol, interval, timestamp, provider)
);

CREATE TABLE IF NOT EXISTS fundamentals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    provider TEXT NOT NULL,
    as_of TEXT,
    payload_json TEXT,
    capture_timestamp TEXT NOT NULL,
    UNIQUE(symbol, provider, as_of)
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    provider TEXT NOT NULL,
    trade_time TEXT,
    price REAL,
    qty REAL,
    capture_timestamp TEXT NOT NULL,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS depth (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    provider TEXT NOT NULL,
    side TEXT,
    price REAL,
    qty REAL,
    capture_timestamp TEXT NOT NULL,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS provider_status (
    provider TEXT PRIMARY KEY,
    enabled INTEGER,
    reachable INTEGER,
    authenticated INTEGER,
    capabilities_json TEXT,
    last_success TEXT,
    last_error TEXT,
    latency_ms REAL,
    latest_source_timestamp TEXT,
    mode TEXT,
    notes TEXT,
    updated_at TEXT,
    health_state TEXT,
    auth_status TEXT,
    provider_type TEXT,
    last_http_status INTEGER,
    last_checked TEXT,
    main_role TEXT
);

CREATE TABLE IF NOT EXISTS data_conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    field TEXT,
    provider_a TEXT,
    value_a TEXT,
    timestamp_a TEXT,
    provider_b TEXT,
    value_b TEXT,
    timestamp_b TEXT,
    selected_provider TEXT,
    reason TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS collection_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT,
    finished_at TEXT,
    status TEXT,
    symbols_json TEXT,
    errors_json TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS scanner_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    as_of TEXT,
    payload_json TEXT,
    capture_timestamp TEXT NOT NULL,
    UNIQUE(symbol, as_of)
);
"""


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._ensure_provider_status_columns()
        self._conn.commit()

    def _ensure_provider_status_columns(self):
        cols = {r[1] for r in self._conn.execute("PRAGMA table_info(provider_status)")}
        for name, typ in (
            ("health_state", "TEXT"),
            ("auth_status", "TEXT"),
            ("provider_type", "TEXT"),
            ("last_http_status", "INTEGER"),
            ("last_checked", "TEXT"),
            ("main_role", "TEXT"),
        ):
            if name not in cols:
                self._conn.execute(f"ALTER TABLE provider_status ADD COLUMN {name} {typ}")
        self._ensure_candle_semantics_column()

    def _ensure_candle_semantics_column(self):
        cols = {r[1] for r in self._conn.execute("PRAGMA table_info(candles)")}
        if "semantics_json" not in cols:
            self._conn.execute("ALTER TABLE candles ADD COLUMN semantics_json TEXT")

    def close(self):
        self._conn.close()

    def upsert_symbol(self, canonical: str, name: str = "", aliases: dict | None = None, sector: str = ""):
        self._conn.execute(
            """INSERT INTO symbols(canonical, name, aliases_json, sector, active, updated_at)
               VALUES(?,?,?,?,1,?)
               ON CONFLICT(canonical) DO UPDATE SET
                 name=excluded.name,
                 aliases_json=excluded.aliases_json,
                 sector=excluded.sector,
                 updated_at=excluded.updated_at
            """,
            (canonical.upper(), name, json.dumps(aliases or {}), sector, _now()),
        )
        self._conn.commit()

    def insert_quote(self, q: dict[str, Any]):
        self._conn.execute(
            """INSERT OR IGNORE INTO quotes(
                symbol, provider, last, open, high, low, prev_close, change_pct, volume,
                bid, ask, provider_timestamp, capture_timestamp, freshness_class, provider_mode, raw_reference
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                q.get("symbol"), q.get("provider"), q.get("last"), q.get("open"), q.get("high"), q.get("low"),
                q.get("prev_close"), q.get("change_pct"), q.get("volume"), q.get("bid"), q.get("ask"),
                q.get("provider_timestamp"), q.get("capture_timestamp"), q.get("freshness_class"),
                q.get("provider_mode"), q.get("raw_reference"),
            ),
        )
        self._conn.commit()

    def upsert_candle(self, c: dict[str, Any]):
        # Canonical storage key: prefer normalized UTC when present (never ambiguous legacy labels).
        ts = c.get("normalized_utc_timestamp") or c.get("timestamp")
        semantic_keys = (
            "provider_raw_timestamp", "provider_timezone_if_known",
            "normalized_utc_timestamp", "normalized_cairo_timestamp",
            "timestamp_semantics", "session_date", "effective_session_date",
            "volume_semantics", "volume_interval", "price_observation_type",
            "latest_completed_session", "freshness_class",
            "timestamp_normalization_status",
        )
        semantics = {k: c.get(k) for k in semantic_keys if c.get(k) is not None}
        if semantics and "timestamp_normalization_status" not in semantics:
            if semantics.get("normalized_utc_timestamp"):
                semantics["timestamp_normalization_status"] = "NORMALIZED"
        self._conn.execute(
            """INSERT INTO candles(
                symbol, interval, timestamp, open, high, low, close, volume,
                provider, capture_timestamp, freshness_class, provider_mode, semantics_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(symbol, interval, timestamp, provider) DO UPDATE SET
                open=excluded.open, high=excluded.high, low=excluded.low, close=excluded.close,
                volume=excluded.volume, capture_timestamp=excluded.capture_timestamp,
                freshness_class=excluded.freshness_class, provider_mode=excluded.provider_mode,
                semantics_json=COALESCE(excluded.semantics_json, candles.semantics_json)
            """,
            (
                c.get("symbol"), c.get("interval"), ts, c.get("open"), c.get("high"),
                c.get("low"), c.get("close"), c.get("volume"), c.get("provider"),
                c.get("capture_timestamp"), c.get("freshness_class"), c.get("provider_mode"),
                json.dumps(semantics) if semantics else None,
            ),
        )
        self._conn.commit()

    def insert_conflict(self, c: dict[str, Any]):
        self._conn.execute(
            """INSERT INTO data_conflicts(
                symbol, field, provider_a, value_a, timestamp_a, provider_b, value_b, timestamp_b,
                selected_provider, reason, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                c.get("symbol"), c.get("field"), c.get("provider_a"), str(c.get("value_a")),
                c.get("timestamp_a"), c.get("provider_b"), str(c.get("value_b")), c.get("timestamp_b"),
                c.get("selected_provider"), c.get("reason"), c.get("created_at"),
            ),
        )
        self._conn.commit()

    def upsert_provider_status(self, st: dict[str, Any]):
        self._conn.execute(
            """INSERT INTO provider_status(
                provider, enabled, reachable, authenticated, capabilities_json, last_success,
                last_error, latency_ms, latest_source_timestamp, mode, notes, updated_at,
                health_state, auth_status, provider_type, last_http_status, last_checked, main_role
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(provider) DO UPDATE SET
                enabled=excluded.enabled, reachable=excluded.reachable, authenticated=excluded.authenticated,
                capabilities_json=excluded.capabilities_json, last_success=excluded.last_success,
                last_error=excluded.last_error, latency_ms=excluded.latency_ms,
                latest_source_timestamp=excluded.latest_source_timestamp, mode=excluded.mode,
                notes=excluded.notes, updated_at=excluded.updated_at,
                health_state=excluded.health_state, auth_status=excluded.auth_status,
                provider_type=excluded.provider_type, last_http_status=excluded.last_http_status,
                last_checked=excluded.last_checked, main_role=excluded.main_role
            """,
            (
                st.get("name") or st.get("provider"),
                1 if st.get("enabled") else 0,
                None if st.get("reachable") is None else (1 if st.get("reachable") else 0),
                None if st.get("authenticated") is None else (1 if st.get("authenticated") else 0),
                json.dumps(st.get("capabilities") or {}),
                st.get("last_success"), st.get("last_error"), st.get("latency_ms"),
                st.get("latest_source_timestamp"), st.get("mode"), st.get("notes"), _now(),
                st.get("health_state"), st.get("auth_status"), st.get("provider_type"),
                st.get("last_http_status"), st.get("last_checked"), st.get("main_role"),
            ),
        )
        self._conn.commit()

    def start_run(self, symbols: list[str]) -> int:
        cur = self._conn.execute(
            "INSERT INTO collection_runs(started_at, status, symbols_json) VALUES (?,?,?)",
            (_now(), "RUNNING", json.dumps(symbols)),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def finish_run(self, run_id: int, status: str, errors: list[str] | None = None, notes: str = ""):
        self._conn.execute(
            "UPDATE collection_runs SET finished_at=?, status=?, errors_json=?, notes=? WHERE id=?",
            (_now(), status, json.dumps(errors or []), notes, run_id),
        )
        self._conn.commit()

    def upsert_scanner_signal(self, symbol: str, as_of: str, payload: dict[str, Any]):
        self._conn.execute(
            """INSERT INTO scanner_signals(symbol, as_of, payload_json, capture_timestamp)
               VALUES (?,?,?,?)
               ON CONFLICT(symbol, as_of) DO UPDATE SET
                 payload_json=excluded.payload_json, capture_timestamp=excluded.capture_timestamp
            """,
            (symbol, as_of, json.dumps(payload), _now()),
        )
        self._conn.commit()

    def insert_fundamentals(self, symbol: str, provider: str, as_of: str | None, payload: dict[str, Any]):
        self._conn.execute(
            """INSERT OR IGNORE INTO fundamentals(symbol, provider, as_of, payload_json, capture_timestamp)
               VALUES (?,?,?,?,?)""",
            (symbol, provider, as_of or _now()[:10], json.dumps(payload), _now()),
        )
        self._conn.commit()

    def fetch_latest_quotes(self, symbol: str | None = None) -> list[dict]:
        if symbol:
            rows = self._conn.execute(
                "SELECT * FROM quotes WHERE symbol=? ORDER BY capture_timestamp DESC LIMIT 50",
                (symbol.upper(),),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM quotes ORDER BY capture_timestamp DESC LIMIT 200"
            ).fetchall()
        return [dict(r) for r in rows]

    def fetch_candles(self, symbol: str, interval: str = "1d", limit: int = 200) -> list[dict]:
        rows = self._conn.execute(
            """SELECT * FROM candles WHERE symbol=? AND interval=?
               ORDER BY timestamp DESC LIMIT ?""",
            (symbol.upper(), interval, limit),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            sem = d.pop("semantics_json", None)
            if sem:
                try:
                    extra = json.loads(sem)
                    if isinstance(extra, dict):
                        for k, v in extra.items():
                            if v is not None and d.get(k) is None:
                                d[k] = v
                            elif k not in d or d.get(k) is None:
                                d[k] = v
                        # Always prefer stored normalized fields when present
                        for k in (
                            "normalized_utc_timestamp", "normalized_cairo_timestamp",
                            "provider_raw_timestamp", "provider_timezone_if_known",
                            "session_date", "timestamp_semantics", "volume_semantics",
                            "price_observation_type", "timestamp_normalization_status",
                        ):
                            if extra.get(k) is not None:
                                d[k] = extra[k]
                except Exception:
                    pass
            out.append(d)
        return out

    def fetch_conflicts(self, limit: int = 100) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM data_conflicts ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def fetch_provider_status(self) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM provider_status ORDER BY provider").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            # Preserve null semantics for reachable/authenticated
            if "reachable" in d:
                d["reachable"] = None if d["reachable"] is None else bool(d["reachable"])
            if "authenticated" in d:
                d["authenticated"] = None if d["authenticated"] is None else bool(d["authenticated"])
            if d.get("enabled") is not None:
                d["enabled"] = bool(d["enabled"])
            if d.get("capabilities_json"):
                try:
                    d["capabilities"] = json.loads(d["capabilities_json"])
                except Exception:
                    d["capabilities"] = {}
            d["name"] = d.get("provider")
            out.append(d)
        return out

    def fetch_runs(self, limit: int = 20) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM collection_runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def count_symbols(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS c FROM symbols").fetchone()
        return int(row["c"]) if row else 0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
