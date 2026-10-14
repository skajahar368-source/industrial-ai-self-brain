"""Verified maintenance outcomes stored separately from AI suggestions.

Only explicitly human-verified records contribute to historical insights.
This module provides decision support; it does not alter models or control PLCs.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


_REQUIRED = (
    "event_timestamp",
    "machine_id",
    "fault_code",
    "cause",
    "repair_action",
    "repair_successful",
    "verified",
    "verified_by",
    "verification_method",
    "verification_result",
)


def _parse_timestamp(value: Any) -> str:
    raw = str(value).strip()
    if not raw:
        raise ValueError("event_timestamp is required")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("event_timestamp must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _required_text(payload: dict[str, Any], field: str) -> str:
    value = str(payload.get(field, "")).strip()
    if not value:
        raise ValueError(f"{field} is required")
    return value


def _as_bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0"}:
            return False
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    raise ValueError(f"{field} must be a boolean")


class VerifiedMaintenanceLearning:
    """SQLite-backed store for human-verified maintenance outcomes."""

    def __init__(self, db_path: str | Path = "data/verified_maintenance.sqlite3") -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.db_path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS verified_outcomes (
                outcome_id TEXT PRIMARY KEY,
                event_timestamp TEXT NOT NULL,
                machine_id TEXT NOT NULL,
                fault_code TEXT NOT NULL,
                cause TEXT NOT NULL,
                repair_action TEXT NOT NULL,
                repair_successful INTEGER NOT NULL,
                verified INTEGER NOT NULL CHECK (verified = 1),
                verified_by TEXT NOT NULL,
                verification_method TEXT NOT NULL,
                verification_result TEXT NOT NULL,
                before_evidence TEXT,
                after_evidence TEXT,
                recorded_at TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def record(self, payload: dict[str, Any]) -> dict[str, Any]:
        missing = [field for field in _REQUIRED if field not in payload]
        if missing:
            return {"status": "blocked", "fields": missing}

        try:
            if _as_bool(payload["verified"], "verified") is not True:
                return {
                    "status": "blocked",
                    "error": "Only explicitly human-verified outcomes can be recorded as learning evidence.",
                }
            row = {
                "outcome_id": str(uuid4()),
                "event_timestamp": _parse_timestamp(payload["event_timestamp"]),
                "machine_id": _required_text(payload, "machine_id"),
                "fault_code": _required_text(payload, "fault_code").upper(),
                "cause": _required_text(payload, "cause"),
                "repair_action": _required_text(payload, "repair_action"),
                "repair_successful": _as_bool(payload["repair_successful"], "repair_successful"),
                "verified": True,
                "verified_by": _required_text(payload, "verified_by"),
                "verification_method": _required_text(payload, "verification_method"),
                "verification_result": _required_text(payload, "verification_result"),
                "before_evidence": str(payload.get("before_evidence", "")).strip() or None,
                "after_evidence": str(payload.get("after_evidence", "")).strip() or None,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
        except (TypeError, ValueError) as exc:
            return {"status": "blocked", "error": str(exc)}

        with self._connection:
            self._connection.execute(
                """
                INSERT INTO verified_outcomes (
                    outcome_id, event_timestamp, machine_id, fault_code, cause,
                    repair_action, repair_successful, verified, verified_by,
                    verification_method, verification_result, before_evidence,
                    after_evidence, recorded_at
                ) VALUES (
                    :outcome_id, :event_timestamp, :machine_id, :fault_code, :cause,
                    :repair_action, :repair_successful, :verified, :verified_by,
                    :verification_method, :verification_result, :before_evidence,
                    :after_evidence, :recorded_at
                )
                """,
                {**row, "repair_successful": int(row["repair_successful"]), "verified": 1},
            )
        return {
            "status": "recorded",
            "outcome": row,
            "message": "Human-verified maintenance outcome saved as historical evidence.",
            "model_updated": False,
            "control_write_performed": False,
        }

    def insights(
        self,
        machine_id: str | None = None,
        fault_code: str | None = None,
    ) -> dict[str, Any]:
        query = """
            SELECT machine_id, fault_code, cause,
                   COUNT(*) AS verified_cases,
                   SUM(repair_successful) AS successful_repairs,
                   MAX(event_timestamp) AS latest_event,
                   GROUP_CONCAT(DISTINCT repair_action) AS repair_actions
            FROM verified_outcomes
            WHERE verified = 1
        """
        params: list[str] = []
        if machine_id:
            query += " AND machine_id = ?"
            params.append(machine_id.strip())
        if fault_code:
            query += " AND fault_code = ?"
            params.append(fault_code.strip().upper())
        query += " GROUP BY machine_id, fault_code, cause ORDER BY verified_cases DESC, latest_event DESC"
        rows = self._connection.execute(query, params).fetchall()
        patterns = []
        for row in rows:
            count = int(row["verified_cases"])
            successes = int(row["successful_repairs"] or 0)
            patterns.append({
                "machine_id": row["machine_id"],
                "fault_code": row["fault_code"],
                "cause": row["cause"],
                "verified_cases": count,
                "successful_repairs": successes,
                "success_rate": round(successes / count, 3) if count else None,
                "latest_event": row["latest_event"],
                "repair_actions": (row["repair_actions"] or "").split(",") if row["repair_actions"] else [],
                "evidence_status": "human_verified",
                "recommendation_type": "historical_evidence_only",
            })
        return {
            "status": "ok",
            "count": len(patterns),
            "insights": patterns,
            "unverified_ai_suggestions_included": False,
            "model_updated": False,
            "control_write_performed": False,
        }
