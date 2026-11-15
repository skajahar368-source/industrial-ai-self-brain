"""Append-only component lifecycle ledger.

Records installation, inspection and removal events. Recorded usage is historical
evidence; this module does not estimate failure probability or control machinery.
"""
from __future__ import annotations

import json
import math
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path("data/component_lifecycle.sqlite3")
EVENT_TYPES = {"install", "inspection", "remove"}
METER_FIELDS = ("runtime_hours", "production_cycles")


def _timestamp(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _meter(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("""
        CREATE TABLE IF NOT EXISTS component_lifecycle_events (
            event_id TEXT PRIMARY KEY,
            machine_id TEXT NOT NULL,
            component_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_timestamp TEXT NOT NULL,
            runtime_hours REAL NOT NULL,
            production_cycles REAL NOT NULL,
            payload_json TEXT NOT NULL
        )
    """)
    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_component_lifecycle_machine_time
        ON component_lifecycle_events(machine_id, event_timestamp)
    """)
    return connection


def _events(connection: sqlite3.Connection, machine_id: str | None = None) -> list[dict[str, Any]]:
    if machine_id is None:
        rows = connection.execute(
            "SELECT * FROM component_lifecycle_events ORDER BY event_timestamp, rowid"
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT * FROM component_lifecycle_events WHERE machine_id=? ORDER BY event_timestamp, rowid",
            (machine_id,),
        ).fetchall()
    result = []
    for row in rows:
        item = json.loads(row["payload_json"])
        item["event_id"] = row["event_id"]
        item["machine_id"] = row["machine_id"]
        item["component_id"] = row["component_id"]
        item["event_type"] = row["event_type"]
        item["event_timestamp"] = row["event_timestamp"]
        item["runtime_hours"] = row["runtime_hours"]
        item["production_cycles"] = row["production_cycles"]
        result.append(item)
    return result


def record_component_event(payload: dict[str, Any], db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"status": "rejected", "error": "payload must be an object"}
    event_type = str(payload.get("event_type", "")).strip().lower()
    machine_id = str(payload.get("machine_id", "")).strip()
    component_id = str(payload.get("component_id", "")).strip()
    timestamp = _timestamp(payload.get("event_timestamp"))
    runtime = _meter(payload.get("runtime_hours"))
    cycles = _meter(payload.get("production_cycles"))
    if event_type not in EVENT_TYPES:
        return {"status": "rejected", "error": "event_type must be install, inspection, or remove"}
    if not machine_id or not component_id:
        return {"status": "rejected", "error": "machine_id and component_id are required"}
    if timestamp is None:
        return {"status": "rejected", "error": "event_timestamp must be a valid ISO-8601 timestamp"}
    if runtime is None or cycles is None:
        return {"status": "rejected", "error": "runtime_hours and production_cycles must be non-negative numbers"}

    if event_type == "install":
        for field in ("part_number", "part_name"):
            if not str(payload.get(field, "")).strip():
                return {"status": "rejected", "error": f"{field} is required for installation"}
    if event_type == "remove" and not str(payload.get("removal_reason", "")).strip():
        return {"status": "rejected", "error": "removal_reason is required for removal"}

    connection = _connect(db_path)
    try:
        history = _events(connection, machine_id)
        state: dict[str, dict[str, Any]] = {}
        for item in history:
            if item["event_type"] == "install":
                state[item["component_id"]] = item
            elif item["event_type"] == "remove":
                state.pop(item["component_id"], None)
        active = component_id in state
        if event_type == "install" and active:
            return {"status": "rejected", "error": "component is already installed on this machine"}
        if event_type in {"inspection", "remove"} and not active:
            return {"status": "rejected", "error": "component has no active installation on this machine"}
        install = state.get(component_id)
        if install and (runtime < install["runtime_hours"] or cycles < install["production_cycles"]):
            return {"status": "rejected", "error": "meter readings cannot decrease below the previous component event"}

        event_id = str(payload.get("event_id", "")).strip()
        if not event_id:
            event_id = f"{machine_id}:{component_id}:{event_type}:{timestamp}"
        if connection.execute(
            "SELECT 1 FROM component_lifecycle_events WHERE event_id=?", (event_id,)
        ).fetchone():
            return {"status": "rejected", "error": "event_id already exists"}

        stored = dict(payload)
        stored.update({
            "event_id": event_id, "machine_id": machine_id, "component_id": component_id,
            "event_type": event_type, "event_timestamp": timestamp,
            "runtime_hours": runtime, "production_cycles": cycles,
        })
        connection.execute(
            """INSERT INTO component_lifecycle_events
            (event_id, machine_id, component_id, event_type, event_timestamp,
             runtime_hours, production_cycles, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (event_id, machine_id, component_id, event_type, timestamp, runtime, cycles,
             json.dumps(stored, sort_keys=True)),
        )
        connection.commit()
        return {"status": "recorded", "event": stored, "control_write_performed": False}
    finally:
        connection.close()


def component_lifecycle_history(
    machine_id: str | None = None, limit: int = 100, db_path: str | Path = DEFAULT_DB_PATH
) -> dict[str, Any]:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
        return {"status": "rejected", "error": "limit must be an integer between 1 and 500"}
    if machine_id is not None and not str(machine_id).strip():
        return {"status": "rejected", "error": "machine_id cannot be empty"}
    connection = _connect(db_path)
    try:
        events = _events(connection, str(machine_id).strip() if machine_id is not None else None)
    finally:
        connection.close()
    events = list(reversed(events))
    selected = events[:limit]
    active: dict[str, dict[str, Any]] = {}
    for item in reversed(events):
        if item["event_type"] == "install":
            active[item["component_id"]] = item
        elif item["event_type"] == "remove":
            active.pop(item["component_id"], None)
    return {
        "status": "ok",
        "machine_id": str(machine_id).strip() if machine_id is not None else None,
        "event_count": len(selected),
        "total_events": len(events),
        "active_component_count": len(active),
        "active_components": list(active.values()),
        "events": selected,
        "lifespan_note": "Actual installed-to-removed usage can be calculated only when both event records exist; active components have no completed lifespan yet.",
        "predictive_failure_claimed": False,
        "control_write_performed": False,
        "plc_write_performed": False,
    }
