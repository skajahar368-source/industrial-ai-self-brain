from __future__ import annotations

from typing import Any

from app.services.health import evaluate_machine_health
from ml.predictive_maintenance import maintenance_risk


def build_degradation_timeline(readings: list[dict[str, Any]]) -> dict[str, Any]:
    """Create an explainable health/risk timeline from historical telemetry."""
    if not readings:
        return {"status": "insufficient_data", "sample_count": 0, "timeline": []}

    ordered = sorted(readings, key=lambda x: str(x.get("timestamp", "")))
    timeline = []
    for reading in ordered:
        health = evaluate_machine_health(reading)
        risk = maintenance_risk(reading)
        timeline.append({
            "timestamp": reading.get("timestamp"),
            "temperature_c": reading.get("temperature_c"),
            "pressure_bar": reading.get("pressure_bar"),
            "vibration_mm_s": reading.get("vibration_mm_s"),
            "fault_code": reading.get("fault_code", "NONE"),
            "health_status": health.get("status"),
            "maintenance_risk": risk.get("maintenance_risk_score"),
        })

    scores = [float(item["maintenance_risk"]) for item in timeline]
    start_score, end_score = scores[0], scores[-1]
    if end_score - start_score >= 15:
        direction = "rapid_deterioration"
    elif end_score > start_score:
        direction = "deteriorating"
    elif end_score < start_score:
        direction = "improving"
    else:
        direction = "stable"

    return {
        "status": "ok",
        "sample_count": len(timeline),
        "direction": direction,
        "start_risk": start_score,
        "end_risk": end_score,
        "risk_change": round(end_score - start_score, 2),
        "timeline": timeline,
    }
