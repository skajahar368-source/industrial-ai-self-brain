from __future__ import annotations

from typing import Any

import pandas as pd

FEATURES = [
    "temperature_c",
    "pressure_bar",
    "vibration_mm_s",
    "cycle_count",
    "downtime_minutes",
]


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def maintenance_risk(reading: dict[str, Any]) -> dict[str, Any]:
    """Return an explainable 0-100 maintenance risk score.

    This MVP uses engineering thresholds and trend signals. It is deliberately
    transparent; a supervised failure model can replace it when labeled
    maintenance/failure history becomes available.
    """
    temperature = float(reading.get("temperature_c", 0))
    pressure = float(reading.get("pressure_bar", 0))
    vibration = float(reading.get("vibration_mm_s", 0))
    downtime = float(reading.get("downtime_minutes", 0))
    fault_code = str(reading.get("fault_code", "NONE")).upper()

    score = 0.0
    factors: list[str] = []

    if temperature >= 80:
        score += 25
        factors.append("high temperature")
    elif temperature >= 65:
        score += 12
        factors.append("elevated temperature")

    if pressure >= 100 or (0 < pressure < 30):
        score += 20
        factors.append("pressure outside normal range")

    if vibration >= 8:
        score += 30
        factors.append("high vibration")
    elif vibration >= 5:
        score += 15
        factors.append("elevated vibration")

    if downtime >= 30:
        score += 15
        factors.append("high downtime")
    elif downtime >= 10:
        score += 8
        factors.append("increasing downtime")

    if fault_code != "NONE":
        score += 10
        factors.append(f"fault code: {fault_code}")

    # A critical machine fault is a high-risk maintenance condition even when
    # individual sensor thresholds have not yet accumulated enough score.
    if fault_code in {"HIGH_TEMP_PRESSURE", "MULTI_PARAMETER_FAULT"}:
        score = max(score, 70)
        factors.append("critical multi-parameter fault")

    score = _clamp(score)

    if score >= 70:
        level = "high"
        action = "Inspect and schedule maintenance before continued production."
    elif score >= 40:
        level = "medium"
        action = "Increase monitoring and plan a maintenance inspection."
    else:
        level = "low"
        action = "Continue normal monitoring."

    return {
        "maintenance_risk_score": round(score, 2),
        "risk_level": level,
        "factors": factors,
        "recommended_action": action,
    }


def score_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    scores = result.apply(lambda row: maintenance_risk(row.to_dict()), axis=1)
    result["maintenance_risk_score"] = [
        item["maintenance_risk_score"] for item in scores
    ]
    result["risk_level"] = [item["risk_level"] for item in scores]
    return result
