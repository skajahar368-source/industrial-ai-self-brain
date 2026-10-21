"""SQLite history for successful Self-Brain maintenance investigation reports."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS maintenance_report_history (
            report_id TEXT PRIMARY KEY,
            machine_id TEXT NOT NULL,
            archived_at_utc TEXT NOT NULL,
            reading_timestamp TEXT,
            fault_code TEXT,
            health_status TEXT,
            risk_level TEXT,
            report_json TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_report_history_machine_time "
        "ON maintenance_report_history(machine_id, archived_at_utc DESC)"
    )
    return connection


def save_report(report: dict[str, Any], db_path: str | Path) -> dict[str, Any]:
    """Persist only successful reports and return archive metadata."""
    if not isinstance(report, dict) or report.get("status") != "ok":
        raise ValueError("Only successful maintenance reports can be archived.")
    machine_id = str(report.get("machine_id") or "").strip()
    if not machine_id:
        raise ValueError("machine_id is required to archive a report.")

    report_id = str(uuid.uuid4())
    archived_at = datetime.now(timezone.utc).isoformat()
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    report_copy = dict(report)
    report_copy["report_id"] = report_id
    report_copy["archived_at_utc"] = archived_at

    connection = _connect(db_path)
    try:
        connection.execute(
            """
            INSERT INTO maintenance_report_history
            (report_id, machine_id, archived_at_utc, reading_timestamp,
             fault_code, health_status, risk_level, report_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id, machine_id, archived_at, summary.get("timestamp"),
                summary.get("fault_code"), summary.get("health_status"),
                summary.get("maintenance_risk_level"),
                json.dumps(report_copy, ensure_ascii=False, sort_keys=True),
            ),
        )
        connection.commit()
    finally:
        connection.close()

    return {"report_id": report_id, "archived_at_utc": archived_at, "history_saved": True}


def list_reports(
    db_path: str | Path, machine_id: str | None = None, limit: int = 20
) -> dict[str, Any]:
    """List recent archived report summaries, optionally filtered by machine."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        return {"status": "rejected", "error": "limit must be an integer between 1 and 100"}
    if machine_id is not None:
        machine_id = str(machine_id).strip()
        if not machine_id:
            return {"status": "rejected", "error": "machine_id cannot be empty"}

    connection = _connect(db_path)
    try:
        query = (
            "SELECT report_id, machine_id, archived_at_utc, reading_timestamp, "
            "fault_code, health_status, risk_level FROM maintenance_report_history "
        )
        if machine_id is None:
            rows = connection.execute(
                query + "ORDER BY archived_at_utc DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = connection.execute(
                query + "WHERE machine_id = ? ORDER BY archived_at_utc DESC LIMIT ?",
                (machine_id, limit),
            ).fetchall()
    finally:
        connection.close()
    return {"status": "ok", "count": len(rows), "reports": [dict(row) for row in rows]}


def get_report(report_id: str, db_path: str | Path) -> dict[str, Any]:
    """Fetch one complete archived report by its opaque ID."""
    report_id = str(report_id).strip()
    if not report_id:
        return {"status": "rejected", "error": "report_id cannot be empty"}

    connection = _connect(db_path)
    try:
        row = connection.execute(
            "SELECT report_json FROM maintenance_report_history WHERE report_id = ?",
            (report_id,),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        return {"status": "not_found", "error": "Archived report not found", "report_id": report_id}
    return json.loads(row["report_json"])
