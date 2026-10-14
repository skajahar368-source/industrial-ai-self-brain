"""Read-only alarm lifecycle tracking with optional SQLite persistence.

This registry records alarm transitions observed from PLC snapshots. It never
sends commands to a PLC and never changes machine operating state.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any


class AlarmManager:
    """Alarm history with optional persistence and acknowledgement metadata.

    When db_path is provided, alarm history survives process restarts.
    Omitting it keeps the manager in-memory only, which is useful for isolated
    tests. Persistence stores Self-Brain's log only; it never writes to a PLC.
    """

    def __init__(
        self,
        max_history: int = 500,
        db_path: str | Path | None = None,
    ) -> None:
        if max_history < 1:
            raise ValueError("max_history must be positive")
        self.max_history = max_history
        self.db_path = str(db_path) if db_path is not None else None
        self._history: list[dict[str, Any]] = []
        self._active_by_machine: dict[str, str] = {}
        self._next_id = 1
        self._lock = RLock()
        self._connection: sqlite3.Connection | None = None

        if self.db_path is not None:
            if self.db_path != ":memory:":
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS alarm_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    next_id INTEGER NOT NULL,
                    history_json TEXT NOT NULL
                )
                """
            )
            self._connection.commit()
            self._load_locked()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load_locked(self) -> None:
        if self._connection is None:
            return
        row = self._connection.execute(
            "SELECT next_id, history_json FROM alarm_state WHERE id = 1"
        ).fetchone()
        if row is None:
            return
        self._next_id = max(1, int(row[0]))
        loaded = json.loads(row[1])
        if not isinstance(loaded, list):
            raise ValueError("Stored alarm history must be a list")
        self._history = [item for item in loaded if isinstance(item, dict)][-self.max_history:]
        self._active_by_machine = {
            item["machine_id"]: item["alarm_id"]
            for item in self._history
            if item.get("active") is True
        }

    def _save_locked(self) -> None:
        if self._connection is None:
            return
        payload = json.dumps(self._history, separators=(",", ":"), ensure_ascii=False)
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO alarm_state (id, next_id, history_json)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    next_id = excluded.next_id,
                    history_json = excluded.history_json
                """,
                (self._next_id, payload),
            )

    def close(self) -> None:
        """Close the optional SQLite connection."""
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    def observe(self, snapshot: dict[str, Any]) -> dict[str, Any] | None:
        """Record a new alarm or close an existing alarm from a PLC snapshot."""
        machine_id = str(snapshot.get("machine_id", "")).strip()
        if not machine_id:
            raise ValueError("machine_id cannot be empty")
        fault_code = str(snapshot.get("fault_code", "NONE")).strip().upper() or "NONE"
        active = bool(snapshot.get("alarm_active", False)) or fault_code != "NONE"
        with self._lock:
            current_id = self._active_by_machine.get(machine_id)
            current = next((item for item in self._history if item["alarm_id"] == current_id), None)
            if active and current and current["fault_code"] == fault_code and current["active"]:
                current["last_seen_at"] = self._now()
                current["machine_state"] = str(snapshot.get("state", "UNKNOWN"))
                self._save_locked()
                return dict(current)
            if current and current["active"]:
                current["active"] = False
                current["cleared_at"] = self._now()
                if not active:
                    self._active_by_machine.pop(machine_id, None)
            if not active:
                self._save_locked()
                return None

            state = str(snapshot.get("state", "UNKNOWN")).upper()
            severity = "critical" if state == "FAULT" else "warning"
            alarm = {
                "alarm_id": f"AL-{self._next_id:06d}",
                "machine_id": machine_id,
                "fault_code": fault_code,
                "severity": severity,
                "message": f"{fault_code.replace('_', ' ').title()} reported by PLC",
                "machine_state": state,
                "active": True,
                "raised_at": self._now(),
                "last_seen_at": self._now(),
                "cleared_at": None,
                "acknowledged": False,
                "acknowledged_at": None,
                "acknowledged_by": None,
                "source": "plc_snapshot",
                "control_write_performed": False,
            }
            self._next_id += 1
            self._history.append(alarm)
            self._active_by_machine[machine_id] = alarm["alarm_id"]
            if len(self._history) > self.max_history:
                removed = self._history.pop(0)
                if self._active_by_machine.get(removed["machine_id"]) == removed["alarm_id"]:
                    self._active_by_machine.pop(removed["machine_id"], None)
            self._save_locked()
            return dict(alarm)

    def acknowledge(self, alarm_id: str, acknowledged_by: str) -> dict[str, Any]:
        """Acknowledge an alarm in Self-Brain's log; this does not affect the PLC."""
        alarm_id = str(alarm_id).strip()
        acknowledged_by = str(acknowledged_by).strip()
        if not alarm_id:
            raise ValueError("alarm_id cannot be empty")
        if not acknowledged_by:
            raise ValueError("acknowledged_by cannot be empty")
        with self._lock:
            alarm = next((item for item in self._history if item["alarm_id"] == alarm_id), None)
            if alarm is None:
                raise ValueError("alarm_id not found")
            if not alarm["acknowledged"]:
                alarm["acknowledged"] = True
                alarm["acknowledged_at"] = self._now()
                alarm["acknowledged_by"] = acknowledged_by
                self._save_locked()
            return dict(alarm)

    def snapshot(self, machine_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            alarms = [
                dict(item) for item in reversed(self._history)
                if machine_id is None or item["machine_id"] == machine_id
            ]
            active = [item for item in alarms if item["active"]]
            return {
                "status": "ok",
                "count": len(alarms),
                "active_count": len(active),
                "alarms": alarms,
                "read_only_to_plc": True,
                "control_write_performed": False,
            }
