from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from threading import RLock


def _default_state_path() -> Path:
    configured = os.getenv("INSIGHTPILOT_STATE_DB", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()

    if "pytest" in sys.modules:
        return Path(tempfile.gettempdir()) / (
            f"insightpilot_state_pytest_{os.getpid()}.db"
        )

    project_root = Path(__file__).resolve().parents[2]
    return project_root / "runtime" / "insightpilot_state.db"


class RuntimeStore:
    """SQLite persistence for V3 conversation state and local telemetry."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else _default_state_path()
        self._lock = RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            self.path,
            timeout=5,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_sessions (
                    session_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversation_sessions_updated
                ON conversation_sessions(updated_at DESC)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_evidence_session_created
                ON evidence_snapshots(session_id, created_at ASC)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry_events (
                    trace_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_telemetry_created
                ON telemetry_events(created_at DESC)
                """
            )
            connection.commit()

    def save_session(
        self,
        session_id: str,
        payload_json: str,
        created_at: str,
        updated_at: str,
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversation_sessions (
                    session_id,
                    payload_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (session_id, payload_json, created_at, updated_at),
            )
            connection.commit()

    def get_session(self, session_id: str) -> str | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM conversation_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        return None if row is None else str(row["payload_json"])

    def list_sessions(self, limit: int = 20) -> list[str]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM conversation_sessions
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [str(row["payload_json"]) for row in rows]

    def delete_session_bundle(self, session_id: str) -> bool:
        """Delete one conversation and all local artifacts tied to it."""
        with self._lock, self._connect() as connection:
            exists = connection.execute(
                """
                SELECT 1
                FROM conversation_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()

            if exists is None:
                return False

            connection.execute(
                "DELETE FROM evidence_snapshots WHERE session_id = ?",
                (session_id,),
            )
            connection.execute(
                "DELETE FROM telemetry_events WHERE session_id = ?",
                (session_id,),
            )
            connection.execute(
                "DELETE FROM conversation_sessions WHERE session_id = ?",
                (session_id,),
            )
            connection.commit()
            return True

    def clear_sessions(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM conversation_sessions")
            connection.commit()

    def save_evidence(
        self,
        snapshot_id: str,
        session_id: str,
        payload_json: str,
        created_at: str,
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO evidence_snapshots (
                    snapshot_id,
                    session_id,
                    payload_json,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(snapshot_id) DO UPDATE SET
                    payload_json = excluded.payload_json
                """,
                (snapshot_id, session_id, payload_json, created_at),
            )
            connection.commit()

    def list_evidence(self, session_id: str) -> list[str]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM evidence_snapshots
                WHERE session_id = ?
                ORDER BY created_at ASC
                """,
                (session_id,),
            ).fetchall()
        return [str(row["payload_json"]) for row in rows]

    def clear_evidence(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM evidence_snapshots")
            connection.commit()

    def save_trace(
        self,
        trace_id: str,
        session_id: str,
        payload_json: str,
        created_at: str,
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO telemetry_events (
                    trace_id,
                    session_id,
                    payload_json,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(trace_id) DO UPDATE SET
                    payload_json = excluded.payload_json
                """,
                (trace_id, session_id, payload_json, created_at),
            )
            connection.commit()

    def list_traces(self, limit: int = 50) -> list[str]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM telemetry_events
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [str(row["payload_json"]) for row in rows]

    def clear_traces(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM telemetry_events")
            connection.commit()


runtime_store = RuntimeStore()
