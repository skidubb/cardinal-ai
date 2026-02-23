"""DuckDB-backed storage for all dynamic agent state.

Concurrency note: DuckDB uses MVCC internally and supports concurrent reads from
a single process. However, only one writer connection is allowed at a time per database
file. For multi-process deployments (e.g., Streamlit with multiple workers), external
locking or a separate database per process is required.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import duckdb

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS experience_logs (
    id INTEGER PRIMARY KEY DEFAULT nextval('exp_seq'),
    role VARCHAR NOT NULL,
    lesson TEXT NOT NULL,
    timestamp VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS preferences (
    role VARCHAR PRIMARY KEY,
    data JSON NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR PRIMARY KEY,
    agent_role VARCHAR NOT NULL,
    title VARCHAR,
    parent_session_id VARCHAR,
    metadata JSON DEFAULT '{}',
    created_at VARCHAR NOT NULL,
    updated_at VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY DEFAULT nextval('msg_seq'),
    session_id VARCHAR NOT NULL,
    role VARCHAR NOT NULL,
    content TEXT NOT NULL,
    timestamp VARCHAR NOT NULL,
    metadata JSON DEFAULT '{}',
    -- session_id references sessions(id) logically, no FK constraint for multi-connection compat
);

CREATE TABLE IF NOT EXISTS debate_sessions (
    id VARCHAR PRIMARY KEY,
    question TEXT NOT NULL,
    agent_roles JSON NOT NULL,
    total_rounds INTEGER NOT NULL,
    rounds JSON DEFAULT '[]',
    synthesis TEXT,
    status VARCHAR DEFAULT 'in_progress',
    created_at VARCHAR NOT NULL,
    updated_at VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS causal_traces (
    event_id VARCHAR PRIMARY KEY,
    graph_data JSON NOT NULL,
    node_count INTEGER DEFAULT 0,
    created_at VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS evaluation_runs (
    id VARCHAR PRIMARY KEY,
    question_id VARCHAR NOT NULL,
    mode VARCHAR NOT NULL,
    output_text TEXT,
    cost FLOAT,
    duration_seconds FLOAT,
    judge_scores JSON,
    trace_metrics JSON,
    created_at VARCHAR NOT NULL
);
"""


class DuckDBStore:
    """Single DuckDB database for all agent dynamic state."""

    def __init__(self, db_path: str | Path = "data/agent_memory.duckdb") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(self.db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables if they don't exist."""
        # Create sequences first (ignore if exists)
        try:
            self.conn.execute("CREATE SEQUENCE exp_seq START 1")
        except duckdb.CatalogException:
            pass
        try:
            self.conn.execute("CREATE SEQUENCE msg_seq START 1")
        except duckdb.CatalogException:
            pass
        self.conn.execute(SCHEMA_SQL)

    def close(self) -> None:
        self.conn.close()

    # -- Experience log operations --

    def add_lesson(self, role: str, lesson: str, timestamp: str) -> None:
        self.conn.execute(
            "INSERT INTO experience_logs (role, lesson, timestamp) VALUES (?, ?, ?)",
            [role, lesson, timestamp],
        )
        # Trim to most recent 50 per role
        self.conn.execute(
            """DELETE FROM experience_logs WHERE role = ? AND id NOT IN (
                 SELECT id FROM experience_logs WHERE role = ? ORDER BY id DESC LIMIT 50
               )""",
            [role, role],
        )

    def get_lessons(self, role: str, limit: int = 50) -> list[tuple[str, str]]:
        """Returns list of (timestamp, lesson) tuples."""
        return self.conn.execute(
            "SELECT timestamp, lesson FROM experience_logs WHERE role = ? ORDER BY id DESC LIMIT ?",
            [role, limit],
        ).fetchall()

    # -- Preference operations --

    def save_preferences(self, role: str, data: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO preferences (role, data) VALUES (?, ?::JSON)",
            [role, json.dumps(data, default=str)],
        )

    def load_preferences(self, role: str) -> dict[str, Any] | None:
        result = self.conn.execute(
            "SELECT data FROM preferences WHERE role = ?", [role]
        ).fetchone()
        if result:
            val = result[0]
            return json.loads(val) if isinstance(val, str) else val  # type: ignore[no-any-return]
        return None

    # -- Session operations --

    def save_session(
        self,
        session_id: str,
        agent_role: str,
        title: str | None,
        parent_session_id: str | None,
        metadata: dict[str, Any],
        created_at: str,
        updated_at: str,
        messages: list[dict[str, Any]],
    ) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO sessions
               (id, agent_role, title, parent_session_id, metadata, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?::JSON, ?, ?)""",
            [
                session_id,
                agent_role,
                title,
                parent_session_id,
                json.dumps(metadata, default=str),
                created_at,
                updated_at,
            ],
        )
        # Delete existing messages for this session, then re-insert
        self.conn.execute("DELETE FROM messages WHERE session_id = ?", [session_id])
        for msg in messages:
            self.conn.execute(
                """INSERT INTO messages (session_id, role, content, timestamp, metadata)
                   VALUES (?, ?, ?, ?, ?::JSON)""",
                [
                    session_id,
                    msg["role"],
                    msg["content"],
                    msg["timestamp"],
                    json.dumps(msg.get("metadata", {}), default=str),
                ],
            )

    def load_session(
        self, session_id: str, agent_role: str | None = None
    ) -> dict[str, Any] | None:
        if agent_role:
            row = self.conn.execute(
                "SELECT * FROM sessions WHERE id = ? AND agent_role = ?",
                [session_id, agent_role],
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT * FROM sessions WHERE id = ?", [session_id]
            ).fetchone()
        if not row:
            return None

        cols = ["id", "agent_role", "title", "parent_session_id", "metadata",
                "created_at", "updated_at"]
        session_data = dict(zip(cols, row))
        if isinstance(session_data["metadata"], str):
            session_data["metadata"] = json.loads(session_data["metadata"])

        msg_rows = self.conn.execute(
            "SELECT role, content, timestamp, metadata"
            " FROM messages WHERE session_id = ? ORDER BY id",
            [session_id],
        ).fetchall()
        session_data["messages"] = [
            {
                "role": m[0],
                "content": m[1],
                "timestamp": m[2],
                "metadata": json.loads(m[3]) if isinstance(m[3], str) else m[3],
            }
            for m in msg_rows
        ]
        return session_data

    def list_sessions(
        self, agent_role: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        if agent_role:
            rows = self.conn.execute(
                """SELECT id, agent_role, title, parent_session_id, metadata,
                          created_at, updated_at
                   FROM sessions WHERE agent_role = ?
                   ORDER BY updated_at DESC LIMIT ?""",
                [agent_role, limit],
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT id, agent_role, title, parent_session_id, metadata,
                          created_at, updated_at
                   FROM sessions ORDER BY updated_at DESC LIMIT ?""",
                [limit],
            ).fetchall()

        cols = ["id", "agent_role", "title", "parent_session_id", "metadata",
                "created_at", "updated_at"]
        results = []
        for row in rows:
            d = dict(zip(cols, row))
            if isinstance(d["metadata"], str):
                d["metadata"] = json.loads(d["metadata"])
            # Count messages
            count = self.conn.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id = ?", [d["id"]]
            ).fetchone()
            d["message_count"] = count[0] if count else 0
            results.append(d)
        return results

    def delete_old_sessions(self, max_age_days: int = 90) -> int:
        """Delete sessions older than max_age_days. Returns count of deleted sessions."""
        self.conn.execute(
            """DELETE FROM messages WHERE session_id IN (
                 SELECT id FROM sessions
                 WHERE CAST(updated_at AS TIMESTAMP) < CURRENT_TIMESTAMP - INTERVAL ? DAY
               )""",
            [max_age_days],
        )
        result2 = self.conn.execute(
            """DELETE FROM sessions
               WHERE CAST(updated_at AS TIMESTAMP) < CURRENT_TIMESTAMP - INTERVAL ? DAY
               RETURNING id""",
            [max_age_days],
        )
        deleted = result2.fetchall()
        return len(deleted)

    def delete_session(self, session_id: str) -> bool:
        exists = self.conn.execute(
            "SELECT id FROM sessions WHERE id = ?", [session_id]
        ).fetchone()
        if not exists:
            return False
        self.conn.execute("DELETE FROM messages WHERE session_id = ?", [session_id])
        self.conn.execute("DELETE FROM sessions WHERE id = ?", [session_id])
        return True

    # -- Debate session operations --

    def save_debate(self, debate_data: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO debate_sessions
               (id, question, agent_roles, total_rounds, rounds, synthesis, status,
                created_at, updated_at)
               VALUES (?, ?, ?::JSON, ?, ?::JSON, ?, ?, ?, ?)""",
            [
                debate_data["id"],
                debate_data["question"],
                json.dumps(debate_data["agent_roles"]),
                debate_data["total_rounds"],
                json.dumps(debate_data["rounds"], default=str),
                debate_data.get("synthesis"),
                debate_data.get("status", "in_progress"),
                debate_data["created_at"],
                debate_data["updated_at"],
            ],
        )

    def load_debate(self, debate_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM debate_sessions WHERE id = ?", [debate_id]
        ).fetchone()
        if not row:
            return None
        cols = ["id", "question", "agent_roles", "total_rounds", "rounds",
                "synthesis", "status", "created_at", "updated_at"]
        data = dict(zip(cols, row))
        for field in ("agent_roles", "rounds"):
            if isinstance(data[field], str):
                data[field] = json.loads(data[field])
        return data

    def list_debates(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """SELECT id, question, agent_roles, total_rounds, rounds, synthesis,
                      status, created_at, updated_at
               FROM debate_sessions ORDER BY updated_at DESC LIMIT ?""",
            [limit],
        ).fetchall()
        cols = ["id", "question", "agent_roles", "total_rounds", "rounds",
                "synthesis", "status", "created_at", "updated_at"]
        results = []
        for row in rows:
            d = dict(zip(cols, row))
            for field in ("agent_roles", "rounds"):
                if isinstance(d[field], str):
                    d[field] = json.loads(d[field])
            results.append(d)
        return results

    def delete_debate(self, debate_id: str) -> bool:
        result = self.conn.execute(
            "DELETE FROM debate_sessions WHERE id = ? RETURNING id", [debate_id]
        ).fetchone()
        return result is not None

    # -- Causal trace operations --

    def save_causal_trace(self, event_id: str, graph_data: dict[str, Any]) -> None:
        from datetime import datetime
        node_count = len(graph_data.get("nodes", {}))
        self.conn.execute(
            """INSERT OR REPLACE INTO causal_traces
               (event_id, graph_data, node_count, created_at)
               VALUES (?, ?::JSON, ?, ?)""",
            [event_id, json.dumps(graph_data, default=str), node_count, datetime.now().isoformat()],
        )

    def load_causal_trace(self, event_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT event_id, graph_data, node_count, created_at"
            " FROM causal_traces WHERE event_id = ?",
            [event_id],
        ).fetchone()
        if not row:
            return None
        data = row[1]
        if isinstance(data, str):
            data = json.loads(data)
        return {"event_id": row[0], "graph_data": data, "node_count": row[2], "created_at": row[3]}

    def list_causal_traces(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT event_id, node_count, created_at"
            " FROM causal_traces ORDER BY created_at DESC LIMIT ?",
            [limit],
        ).fetchall()
        return [{"event_id": r[0], "node_count": r[1], "created_at": r[2]} for r in rows]

    # -- Evaluation run operations --

    def save_evaluation_run(self, data: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO evaluation_runs
               (id, question_id, mode, output_text, cost, duration_seconds,
                judge_scores, trace_metrics, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?::JSON, ?::JSON, ?)""",
            [
                data["id"],
                data["question_id"],
                data["mode"],
                data.get("output_text"),
                data.get("cost", 0.0),
                data.get("duration_seconds", 0.0),
                json.dumps(data.get("judge_scores", {})),
                json.dumps(data.get("trace_metrics", {})),
                data["created_at"],
            ],
        )

    def list_evaluation_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """SELECT id, question_id, mode, cost, duration_seconds, judge_scores,
                      trace_metrics, created_at
               FROM evaluation_runs ORDER BY created_at DESC LIMIT ?""",
            [limit],
        ).fetchall()
        cols = ["id", "question_id", "mode", "cost", "duration_seconds",
                "judge_scores", "trace_metrics", "created_at"]
        results = []
        for row in rows:
            d = dict(zip(cols, row))
            for field in ("judge_scores", "trace_metrics"):
                if isinstance(d[field], str):
                    d[field] = json.loads(d[field])
            results.append(d)
        return results
