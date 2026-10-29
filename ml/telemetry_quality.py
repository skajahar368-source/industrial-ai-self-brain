from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from typing import Any

import pandas as pd

SENSOR_FIELDS = ("temperature_c", "pressure_bar", "vibration_mm_s")
DEFAULT_SPIKE_THRESHOLDS = {
    "temperature_c": 15.0,
    "pressure_bar": 20.0,
    "vibration_mm_s": 3.0,
}


def _parse_timestamp(value: Any) -> datetime:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        raise ValueError("timestamp must be a valid ISO-8601 datetime")
    return parsed.to_pydatetime()


def _numeric_sensor_value(reading: dict[str, Any], field: str) -> float | None:
    if field not in reading or reading[field] is None:
        return None
    try:
        value = float(reading[field])
    except (TypeError, ValueError):
        return None
    return value if isfinite(value) else None


def assess_telemetry_quality(
    readings: list[dict[str, Any]],
    *,
    reference_time: str | None = None,
    stale_after_seconds: int = 60,
    stuck_window: int = 3,
    spike_thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Assess telemetry quality without changing or storing readings.

    Readings are ordered by parsed UTC timestamps. Sensor comparisons never
    cross machine boundaries. Returned indices refer to the sorted list.
    """
    if not isinstance(readings, list):
        raise ValueError("readings must be a list")
    if any(not isinstance(item, dict) for item in readings):
        raise ValueError("each reading must be an object")
    if isinstance(stale_after_seconds, bool) or not isinstance(stale_after_seconds, int):
        raise ValueError("stale_after_seconds must be a non-negative integer")
    if stale_after_seconds < 0:
        raise ValueError("stale_after_seconds cannot be negative")
    if isinstance(stuck_window, bool) or not isinstance(stuck_window, int) or stuck_window < 2:
        raise ValueError("stuck_window must be an integer of at least 2")

    thresholds = dict(DEFAULT_SPIKE_THRESHOLDS)
    if spike_thresholds is not None:
        if not isinstance(spike_thresholds, dict):
            raise ValueError("spike_thresholds must be an object")
        unknown = set(spike_thresholds) - set(SENSOR_FIELDS)
        if unknown:
            raise ValueError(f"unsupported spike threshold sensors: {sorted(unknown)}")
        thresholds.update(spike_thresholds)
    for field, threshold in thresholds.items():
        if isinstance(threshold, bool):
            raise ValueError(f"spike threshold for {field} must be a finite positive number")
        try:
            numeric_threshold = float(threshold)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"spike threshold for {field} must be a finite positive number") from exc
        if not isfinite(numeric_threshold) or numeric_threshold <= 0:
            raise ValueError(f"spike threshold for {field} must be a finite positive number")
        thresholds[field] = numeric_threshold

    if not readings:
        return {"status": "insufficient_data", "quality": "unknown", "issues": [], "issue_count": 0, "checked_readings": 0}

    reference = _parse_timestamp(reference_time) if reference_time is not None else datetime.now(timezone.utc)

    parsed_items: list[tuple[datetime | None, dict[str, Any]]] = []
    for reading in readings:
        try:
            timestamp = _parse_timestamp(reading.get("timestamp"))
        except ValueError:
            timestamp = None
        parsed_items.append((timestamp, reading))

    indexed = sorted(
        enumerate(parsed_items),
        key=lambda item: (
            item[1][0] is None,
            item[1][0].timestamp() if item[1][0] is not None else float("inf"),
            item[0],
        ),
    )
    ordered = [pair for _, pair in indexed]
    issues: list[dict[str, Any]] = []
    valid_values: list[dict[str, float | None]] = []

    for index, (timestamp, reading) in enumerate(ordered):
        if timestamp is None:
            issues.append({"type": "invalid_timestamp", "index": index, "message": "Reading timestamp is invalid."})
        else:
            age_seconds = (reference - timestamp).total_seconds()
            if age_seconds > stale_after_seconds:
                issues.append({
                    "type": "stale_reading", "index": index,
                    "age_seconds": round(age_seconds, 2),
                    "message": "Reading is older than the configured freshness window.",
                })
            elif age_seconds < -stale_after_seconds:
                issues.append({
                    "type": "future_timestamp", "index": index,
                    "age_seconds": round(age_seconds, 2),
                    "message": "Reading timestamp is too far ahead of the reference clock.",
                })

        row_values: dict[str, float | None] = {}
        for field in SENSOR_FIELDS:
            value = _numeric_sensor_value(reading, field)
            row_values[field] = value
            if field not in reading or reading[field] is None:
                issues.append({
                    "type": "missing_sensor", "index": index, "sensor": field,
                    "message": f"Required sensor field '{field}' is missing.",
                })
            elif value is None:
                issues.append({
                    "type": "invalid_sensor_value", "index": index, "sensor": field,
                    "message": f"Sensor field '{field}' must be a finite numeric value.",
                })
        valid_values.append(row_values)

    for index in range(1, len(ordered)):
        previous_time, previous = ordered[index - 1]
        current_time, current = ordered[index]
        if previous_time is None or current_time is None:
            continue
        if previous.get("machine_id") != current.get("machine_id"):
            continue
        for field in SENSOR_FIELDS:
            before, after = valid_values[index - 1][field], valid_values[index][field]
            if before is None or after is None:
                continue
            delta = abs(after - before)
            if delta >= thresholds[field]:
                issues.append({
                    "type": "sudden_spike", "index": index, "sensor": field,
                    "delta": round(delta, 4), "threshold": thresholds[field],
                    "message": f"{field} changed sharply between consecutive readings.",
                })

    machine_ids = list(dict.fromkeys(reading.get("machine_id") for _, reading in ordered))
    for machine_id in machine_ids:
        machine_indices = [
            index for index, (_, reading) in enumerate(ordered)
            if reading.get("machine_id") == machine_id
        ]
        for field in SENSOR_FIELDS:
            values = [(index, valid_values[index][field]) for index in machine_indices]
            for start in range(len(values) - stuck_window + 1):
                window = values[start : start + stuck_window]
                numeric = [value for _, value in window]
                if any(value is None for value in numeric):
                    continue
                if len(set(numeric)) == 1:
                    issues.append({
                        "type": "stuck_sensor", "sensor": field, "machine_id": machine_id,
                        "start_index": window[0][0], "end_index": window[-1][0],
                        "value": numeric[0],
                        "message": f"{field} remained unchanged for the configured window.",
                    })
                    break

    return {
        "status": "ok",
        "quality": "good" if not issues else "degraded",
        "issues": issues,
        "issue_count": len(issues),
        "checked_readings": len(ordered),
    }
