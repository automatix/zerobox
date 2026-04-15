"""Audit logging service with SQLite storage (FR-06)."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from zerobox.audit.models import AuditEntry

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT    NOT NULL,
    action    TEXT    NOT NULL,
    source    TEXT    NOT NULL,
    target    TEXT,
    rule_id   TEXT,
    details   TEXT    NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_audit_action    ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_rule_id   ON audit_log(rule_id);
"""


class AuditService:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._ensure_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def log(
        self,
        action: str,
        source: str,
        target: str | None = None,
        rule_id: str | None = None,
        details: dict | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            timestamp=datetime.now(),
            action=action,
            source=source,
            target=target,
            rule_id=rule_id,
            details=details or {},
        )
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO audit_log (timestamp, action, source, target, rule_id, details) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    entry.timestamp.isoformat(),
                    entry.action,
                    entry.source,
                    entry.target,
                    entry.rule_id,
                    json.dumps(entry.details),
                ),
            )
            entry.id = cursor.lastrowid
        return entry

    def query(
        self,
        action: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        rule_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        clauses: list[str] = []
        params: list[str | int] = []

        if action is not None:
            clauses.append("action = ?")
            params.append(action)
        if start is not None:
            clauses.append("timestamp >= ?")
            params.append(start.isoformat())
        if end is not None:
            clauses.append("timestamp <= ?")
            params.append(end.isoformat())
        if rule_id is not None:
            clauses.append("rule_id = ?")
            params.append(rule_id)

        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM audit_log{where} ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            AuditEntry(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                action=row["action"],
                source=row["source"],
                target=row["target"],
                rule_id=row["rule_id"],
                details=json.loads(row["details"]),
            )
            for row in rows
        ]
