from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

TELEMETRY_PATH = Path("data/telemetry_stream.csv")
REQUIRED_FIELDS = (
    "timestamp",
    "machine_id",
    "temperature_c",
    "pressure_bar",
    "vibration_mm_s",
    "cycle_count",
    "downtime_minutes",
    "fault_code",
)
NUMERIC_FIELDS = (
    "temperature_c",
    "pressure_bar",
    "vibration_mm_s",
    "cycle_count",
    "downtime_minutes",
)


def _timestamp(value: Any) -> str:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        raise ValueError("timestamp must be a valid ISO-8601 datetime")
    return parsed.isoformat()


def normalize_reading(payload: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"Missing required telemetry fields: {missing}")

    machine_id = str(payload["machine_id"]).strip()
    if not machine_id:
        raise ValueError("machine_id cannot be empty")

    normalized: dict[str, Any] = {
        "timestamp": _timestamp(payload["timestamp"]),
        "machine_id": machine_id,
        "fault_code": str(payload.get("fault_code", "NONE")).strip() or "NONE",
        "source": str(payload.get("source", "api")).strip() or "api",
        "sequence_id": str(payload.get("sequence_id", "")).strip() or None,
    }

    for field in NUMERIC_FIELDS:
        try:
            value = float(payload[field])
        except (TypeError, ValueError):
            raise ValueError(f"{field} must be numeric") from None
        if value < 0:
            raise ValueError(f"{field} cannot be negative")
        normalized[field] = value

    return normalized


def _load_stream() -> pd.DataFrame:
    if not TELEMETRY_PATH.exists():
        return pd.DataFrame(columns=[*REQUIRED_FIELDS, "source", "sequence_id", "received_at"])
    return pd.read_csv(TELEMETRY_PATH)


def ingest_reading(payload: dict[str, Any]) -> dict[str, Any]:
    reading = normalize_reading(payload)
    stream = _load_stream()

    duplicate = False
    if reading["sequence_id"]:
        duplicate = (
            (stream.get("sequence_id", pd.Series(dtype=str)).astype(str) == reading["sequence_id"])
            & (stream.get("machine_id", pd.Series(dtype=str)).astype(str) == reading["machine_id"])
        ).any()

    if duplicate:
        return {
            "status": "duplicate",
            "machine_id": reading["machine_id"],
            "sequence_id": reading["sequence_id"],
            "message": "Telemetry event already exists; duplicate was not stored.",
        }

    reading["received_at"] = datetime.now(timezone.utc).isoformat()
    updated = pd.concat([stream, pd.DataFrame([reading])], ignore_index=True)
    TELEMETRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    updated.to_csv(TELEMETRY_PATH, index=False)

    return {"status": "accepted", "reading": reading}


def ingest_batch(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    results = []
    accepted = 0
    duplicates = 0

    for payload in payloads:
        try:
            result = ingest_reading(payload)
        except ValueError as exc:
            result = {"status": "rejected", "error": str(exc)}
        results.append(result)
        if result["status"] == "accepted":
            accepted += 1
        elif result["status"] == "duplicate":
            duplicates += 1

    return {
        "count": len(results),
        "accepted": accepted,
        "duplicates": duplicates,
        "rejected": len(results) - accepted - duplicates,
        "results": results,
    }


def recent_telemetry(machine_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")

    stream = _load_stream()
    if machine_id:
        stream = stream[stream["machine_id"].astype(str) == str(machine_id)]

    if stream.empty:
        return []

    stream["timestamp"] = pd.to_datetime(stream["timestamp"], errors="coerce")
    return (
        stream.sort_values("timestamp", ascending=False)
        .head(limit)
        .to_dict(orient="records")
    )
