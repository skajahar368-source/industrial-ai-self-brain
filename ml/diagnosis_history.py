"""Small SQLite-backed history for reviewed Self-Brain diagnosis summaries.

Only diagnosis summaries are stored; raw telemetry and API credentials are not.
This history is advisory and never sends commands to industrial equipment.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(os.environ.get("SELF_BRAIN_HISTORY_DB", "data/self_brain_history.sqlite3"))


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS diagnosis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at TEXT NOT NULL,
            machine_id TEXT NOT NULL,
            severity TEXT NOT NULL,
            predicted_fault TEXT,
            rule_summary TEXT,
            ml_summary TEXT,
            telemetry_quality TEXT,
            explanation_status TEXT,
            details_json TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_diagnosis_history_machine_time "
        "ON diagnosis_history(machine_id, id DESC)"
    )
    return connection


def record_diagnosis(
    record: dict[str, Any], *, db_path: str | Path | None = None
) -> dict[str, Any]:
    """Store a bounded, sanitized diagnosis summary and return its history ID."""
    machine_id = record.get("machine_id")
    if not isinstance(machine_id, str) or not machine_id.strip():
        raise ValueError("machine_id must be a non-empty string")
    if len(machine_id) > 100:
        raise ValueError("machine_id cannot exceed 100 characters")

    severity = str(record.get("severity", "unknown")).lower()
    if severity not in {"low", "medium", "high", "critical", "unknown"}:
        severity = "unknown"

    safe_details = {
        "data_provenance": str(record.get("data_provenance", "unspecified"))[:200],
        "read_only": True,
        "real_plc_connected": False,
        "write_commands_supported": False,
        "human_decision_required": True,
    }
    connection = _connect(db_path)
    try:
        cursor = connection.execute(
            """
            INSERT INTO diagnosis_history
            (recorded_at, machine_id, severity, predicted_fault, rule_summary,
             ml_summary, telemetry_quality, explanation_status, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                machine_id.strip(),
                severity,
                str(record.get("predicted_fault", ""))[:120] or None,
                str(record.get("rule_summary", ""))[:500] or None,
                str(record.get("ml_summary", ""))[:500] or None,
                str(record.get("telemetry_quality", "unknown"))[:40],
                str(record.get("explanation_status", "not_requested"))[:40],
                json.dumps(safe_details, sort_keys=True),
            ),
        )
        connection.commit()
        return {"status": "recorded", "history_id": int(cursor.lastrowid)}
    finally:
        connection.close()


def list_diagnoses(
    *, machine_id: str | None = None, limit: int = 20, db_path: str | Path | None = None
) -> dict[str, Any]:
    """Return newest diagnosis summaries, optionally filtered by machine."""
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer between 1 and 100")
    if machine_id is not None and (not machine_id.strip() or len(machine_id) > 100):
        raise ValueError("machine_id must contain 1 to 100 characters")

    connection = _connect(db_path)
    try:
        if machine_id is None:
            rows = connection.execute(
                "SELECT * FROM diagnosis_history ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM diagnosis_history WHERE machine_id = ? "
                "ORDER BY id DESC LIMIT ?",
                (machine_id.strip(), limit),
            ).fetchall()
        history = []
        for row in rows:
            item = dict(row)
            item["details"] = json.loads(item.pop("details_json"))
            history.append(item)
        return {"status": "ok", "count": len(history), "history": history}
    finally:
        connection.close()
