from __future__ import annotations

from typing import Any


CAUSE_RULES = [
    {
        "cause": "Overheating",
        "conditions": lambda p: float(p.get("temperature_c", 0)) >= 80,
        "evidence": "Temperature is at or above the high-temperature threshold.",
        "action": "Inspect cooling, airflow, lubrication, and thermal load.",
    },
    {
        "cause": "Excessive vibration",
        "conditions": lambda p: float(p.get("vibration_mm_s", 0)) >= 8,
        "evidence": "Vibration is at or above the high-vibration threshold.",
        "action": "Inspect bearings, alignment, looseness, and rotating components.",
    },
    {
        "cause": "Abnormal pressure",
        "conditions": lambda p: float(p.get("pressure_bar", 0)) >= 100
        or (0 < float(p.get("pressure_bar", 0)) < 30),
        "evidence": "Pressure is outside the expected operating range.",
        "action": "Inspect pressure regulation, valves, filters, and process load.",
    },
    {
        "cause": "Extended downtime event",
        "conditions": lambda p: float(p.get("downtime_minutes", 0)) >= 30,
        "evidence": "Recorded downtime is at least 30 minutes.",
        "action": "Review the downtime event log and maintenance intervention.",
    },
    {
        "cause": "Recorded machine fault",
        "conditions": lambda p: str(p.get("fault_code", "")).strip().lower() not in {"", "none", "nan"},
        "evidence": "A fault code is present in the machine record.",
        "action": "Check the fault-code definition and corresponding maintenance procedure.",
    },
]


def analyze_root_causes(payload: dict[str, Any]) -> dict[str, Any]:
    findings = []

    for rule in CAUSE_RULES:
        try:
            matched = rule["conditions"](payload)
        except (TypeError, ValueError):
            matched = False

        if matched:
            findings.append(
                {
                    "cause": rule["cause"],
                    "evidence": rule["evidence"],
                    "recommended_action": rule["action"],
                }
            )

    if not findings:
        return {
            "status": "no_significant_cause_detected",
            "cause_count": 0,
            "causes": [],
            "summary": "The supplied reading does not match the current root-cause rules.",
        }

    priority = "high" if len(findings) >= 3 else "medium" if len(findings) == 2 else "low"

    return {
        "status": "causes_detected",
        "cause_count": len(findings),
        "priority": priority,
        "causes": findings,
        "summary": f"{len(findings)} potential contributing cause(s) detected.",
    }
