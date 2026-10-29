"""Rule-based advisory diagnosis for simulated PLC telemetry.

This module is deterministic and is not an AI model or a machine-control system.
"""
from typing import Any


def diagnose_virtual_plc_reading(reading: dict[str, Any]) -> dict[str, Any]:
    """Return explainable findings from one validated simulated telemetry reading."""
    if not isinstance(reading, dict):
        raise ValueError("reading must be a dictionary")

    required = ("machine_id", "temperature_c", "pressure_bar", "vibration_mm_s", "fault_code")
    missing = [field for field in required if field not in reading]
    if missing:
        raise ValueError(f"missing required fields: {missing}")

    findings: list[dict[str, str]] = []
    checks = (
        ("temperature_c", 85.0, "High temperature", "Check cooling, lubrication, and temperature sensor validity."),
        ("pressure_bar", 90.0, "High pressure", "Have a qualified technician verify pressure regulation and the sensor."),
        ("vibration_mm_s", 7.0, "High vibration", "Inspect mounting, alignment, bearings, and tooling after following site safety procedures."),
    )
    for field, threshold, title, recommendation in checks:
        value = reading[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{field} must be numeric")
        if value >= threshold:
            findings.append({
                "code": f"HIGH_{field.upper()}",
                "severity": "high",
                "title": title,
                "observed_value": value,
                "threshold": threshold,
                "recommendation": recommendation,
            })

    fault_code = str(reading["fault_code"]).strip()
    if fault_code not in ("", "NONE") and not any(item["code"] == "HIGH_TEMPERATURE_C" for item in findings):
        findings.append({
            "code": "SIMULATOR_FAULT_CODE",
            "severity": "high" if fault_code.startswith("HIGH") else "warning",
            "title": "Simulator reported a fault code",
            "observed_value": fault_code,
            "threshold": "rule-based fault-code check",
            "recommendation": "Review the machine alarm and follow the approved maintenance procedure; do not rely on this advisory alone.",
        })

    severity = "high" if any(item["severity"] == "high" for item in findings) else ("warning" if findings else "normal")
    return {
        "status": "ok",
        "analysis_type": "deterministic_rules",
        "machine_id": str(reading["machine_id"]),
        "severity": severity,
        "finding_count": len(findings),
        "findings": findings,
        "human_decision_required": True,
        "automated_machine_action": False,
        "note": "Advisory for simulated telemetry only; verify with approved procedures and qualified personnel.",
    }
