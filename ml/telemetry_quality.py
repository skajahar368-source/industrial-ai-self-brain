from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd


SENSOR_FIELDS = ("temperature_c", "pressure_bar", "vibration_mm_s")


def _parse_timestamp(value: Any) -> datetime:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        raise ValueError("timestamp must be a valid ISO-8601 datetime")
    return parsed.to_pydatetime()


def assess_telemetry_quality(
    readings: list[dict[str, Any]],
    *,
    reference_time: str | None = None,
    stale_after_seconds: int = 60,
    stuck_window: int = 3,
    spike_thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Assess sensor-data quality without changing or storing telemetry.

    The function is deterministic when reference_time is supplied. It flags:
    missing sensor fields, stale readings, repeated sensor values, and
    unusually large step-to-step changes.
    """
    if stale_after_seconds < 0:
        raise ValueError("stale_after_seconds cannot be negative")
    if stuck_window < 2:
        raise ValueError("stuck_window must be at least 2")

    if not readings:
        return {
            "status": "insufficient_data",
            "quality": "unknown",
            "issues": [],
            "issue_count": 0,
        }

    reference = (
        _parse_timestamp(reference_time)
        if reference_time is not None
        else datetime.now(timezone.utc)
    )

    thresholds = spike_thresholds or {
        "temperature_c": 15.0,
        "pressure_bar": 20.0,
        "vibration_mm_s": 3.0,
    }

    issues: list[dict[str, Any]] = []
    ordered = sorted(readings, key=lambda item: str(item.get("timestamp", "")))

    for index, reading in enumerate(ordered):
        timestamp_value = reading.get("timestamp")
        try:
            timestamp = _parse_timestamp(timestamp_value)
        except ValueError:
            issues.append({
                "type": "invalid_timestamp",
                "index": index,
                "message": "Reading timestamp is invalid.",
            })
            continue

        age_seconds = (reference - timestamp).total_seconds()
        if age_seconds > stale_after_seconds:
            issues.append({
                "type": "stale_reading",
                "index": index,
                "age_seconds": round(age_seconds, 2),
                "message": "Reading is older than the configured freshness window.",
            })

        for field in SENSOR_FIELDS:
            if field not in reading or reading[field] is None:
                issues.append({
                    "type": "missing_sensor",
                    "index": index,
                    "sensor": field,
                    "message": f"Required sensor field '{field}' is missing.",
                })

        if index == 0:
            continue

        previous = ordered[index - 1]
        for field in SENSOR_FIELDS:
            if field not in previous or field not in reading:
                continue
            try:
                delta = abs(float(reading[field]) - float(previous[field]))
            except (TypeError, ValueError):
                continue
            if delta >= thresholds[field]:
                issues.append({
                    "type": "sudden_spike",
                    "index": index,
                    "sensor": field,
                    "delta": round(delta, 4),
                    "threshold": thresholds[field],
                    "message": f"{field} changed sharply between consecutive readings.",
                })

    for field in SENSOR_FIELDS:
        values = []
        for reading in ordered:
            if field not in reading or reading[field] is None:
                values = []
                break
            try:
                values.append(float(reading[field]))
            except (TypeError, ValueError):
                values = []
                break

        if len(values) >= stuck_window:
            for start in range(len(values) - stuck_window + 1):
                window = values[start : start + stuck_window]
                if len(set(window)) == 1:
                    issues.append({
                        "type": "stuck_sensor",
                        "sensor": field,
                        "start_index": start,
                        "end_index": start + stuck_window - 1,
                        "value": window[0],
                        "message": f"{field} remained unchanged for the configured window.",
                    })
                    break

    quality = "good" if not issues else "degraded"
    return {
        "status": "ok",
        "quality": quality,
        "issues": issues,
        "issue_count": len(issues),
        "checked_readings": len(ordered),
    }
