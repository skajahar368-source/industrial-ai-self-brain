from __future__ import annotations

from typing import Any


def evaluate_machine_health(data: dict[str, Any]) -> dict[str, Any]:
    """Return a transparent, rule-based machine-health assessment.

    This first version intentionally uses explainable thresholds. ML models
    can be introduced later without changing the API contract.
    """
    temperature = float(data.get("temperature_c", 0))
    pressure = float(data.get("pressure_bar", 0))
    vibration = float(data.get("vibration_mm_s", 0))

    warnings: list[str] = []

    if temperature >= 80:
        warnings.append("High temperature")
    elif temperature >= 65:
        warnings.append("Elevated temperature")

    if pressure >= 100:
        warnings.append("High pressure")
    elif 0 < pressure < 30:
        warnings.append("Low pressure")

    if vibration >= 8:
        warnings.append("High vibration")
    elif vibration >= 5:
        warnings.append("Elevated vibration")

    if any(w.startswith("High") for w in warnings):
        status = "critical"
    elif warnings:
        status = "warning"
    else:
        status = "normal"

    return {
        "status": status,
        "warnings": warnings,
        "recommendation": recommendation_for(status, warnings),
    }


def recommendation_for(status: str, warnings: list[str]) -> str:
    if status == "critical":
        return "Inspect the machine before returning it to normal production."
    if status == "warning":
        return "Schedule inspection and continue monitoring the affected signals."
    return "No immediate maintenance action indicated by the current thresholds."
