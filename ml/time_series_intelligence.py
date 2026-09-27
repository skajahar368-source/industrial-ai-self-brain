from __future__ import annotations

from statistics import mean
from typing import Any


def _slope(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return (values[-1] - values[0]) / (len(values) - 1)


def analyze_trends(readings: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze recent telemetry for directional deterioration signals.

    This is an explainable trend layer, not a trained failure predictor.
    """
    if not readings:
        return {
            "status": "insufficient_data",
            "sample_count": 0,
            "signals": [],
            "trend": "unknown",
        }

    ordered = sorted(readings, key=lambda x: str(x.get("timestamp", "")))
    metrics = {
        "temperature_c": [float(x["temperature_c"]) for x in ordered],
        "pressure_bar": [float(x["pressure_bar"]) for x in ordered],
        "vibration_mm_s": [float(x["vibration_mm_s"]) for x in ordered],
        "downtime_minutes": [float(x["downtime_minutes"]) for x in ordered],
    }
    slopes = {name: round(_slope(values), 4) for name, values in metrics.items()}
    signals: list[str] = []

    if len(ordered) >= 3:
        if slopes["temperature_c"] >= 1.0:
            signals.append("temperature_rising")
        if slopes["vibration_mm_s"] >= 0.5:
            signals.append("vibration_rising")
        if slopes["pressure_bar"] >= 1.0:
            signals.append("pressure_rising")
        if slopes["downtime_minutes"] >= 0.5:
            signals.append("downtime_increasing")

    deterioration = any(
        signal in signals
        for signal in ("temperature_rising", "vibration_rising", "pressure_rising", "downtime_increasing")
    )
    return {
        "status": "ok",
        "sample_count": len(ordered),
        "trend": "deteriorating" if deterioration else "stable",
        "signals": signals,
        "slopes_per_sample": slopes,
        "latest": {key: values[-1] for key, values in metrics.items()},
        "averages": {key: round(mean(values), 3) for key, values in metrics.items()},
    }
