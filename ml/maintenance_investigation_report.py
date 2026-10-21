"""Build a structured, evidence-labeled maintenance investigation report.

This module formats existing Self-Brain evidence. It does not perform a new
diagnosis, train models, or send commands to industrial controls.
"""
from __future__ import annotations

from typing import Any


def _numeric_measurement_count(reading: dict[str, Any]) -> int:
    """Count numeric telemetry fields without treating booleans as measurements."""
    metadata = {"machine_id", "timestamp", "fault_code", "status", "scenario"}
    return sum(
        1
        for key, value in reading.items()
        if key not in metadata
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
    )


def build_maintenance_investigation_report(assistant_result: dict[str, Any]) -> dict[str, Any]:
    """Transform an industrial-assistant response into a structured report."""
    if not isinstance(assistant_result, dict):
        return {"status": "blocked", "error": "Assistant result must be an object."}

    if assistant_result.get("status") != "ok":
        return {
            "status": assistant_result.get("status", "blocked"),
            "machine_id": assistant_result.get("machine_id"),
            "error": assistant_result.get(
                "error",
                assistant_result.get("answer", "Assistant could not produce evidence."),
            ),
        }

    evidence = assistant_result.get("evidence")
    if not isinstance(evidence, dict):
        return {"status": "blocked", "error": "Assistant evidence must be an object."}

    reading = evidence.get("latest_reading", {})
    health = evidence.get("health", {})
    risk = evidence.get("maintenance_risk", {})
    anomaly = evidence.get("anomaly", {})
    root_cause = evidence.get("root_cause", {})
    verified = evidence.get("verified_maintenance_context", {})
    if not all(isinstance(value, dict) for value in (reading, health, risk, anomaly, root_cause, verified)):
        return {"status": "blocked", "error": "Required evidence sections must be objects."}

    rule_findings = root_cause.get("causes", [])
    if not isinstance(rule_findings, list):
        rule_findings = []
    verified_records = verified.get("evidence", [])
    if not isinstance(verified_records, list):
        verified_records = []

    recommended_checks = []
    for finding in rule_findings:
        if not isinstance(finding, dict):
            continue
        action = finding.get("recommended_action")
        if action:
            recommended_checks.append({
                "check": str(action),
                "source": "deterministic_root_cause_rule",
                "cause_label": str(finding.get("cause", "Potential contributing cause")),
            })

    missing_context = []
    if not reading.get("timestamp"):
        missing_context.append("reading_timestamp")
    if not reading.get("fault_code"):
        missing_context.append("fault_code")
    measurement_count = _numeric_measurement_count(reading)
    if measurement_count == 0:
        missing_context.append("numeric_sensor_measurements")
    anomaly_label = anomaly.get("anomaly_label")
    anomaly_flagged = None if anomaly_label is None else anomaly_label == -1

    return {
        "status": "ok",
        "report_version": "3.1",
        "machine_id": assistant_result.get("machine_id"),
        "question": assistant_result.get("question"),
        "summary": {
            "health_status": health.get("status", "unknown"),
            "maintenance_risk_level": risk.get("risk_level", "unknown"),
            "maintenance_risk_score": risk.get("maintenance_risk_score"),
            "anomaly_flagged": anomaly_flagged,
            "fault_code": reading.get("fault_code"),
            "timestamp": reading.get("timestamp"),
        },
        "evidence_quality": {
            "status": "partial" if missing_context else "available",
            "missing_context": missing_context,
            "numeric_measurement_count": measurement_count,
            "recommended_check_count": len(recommended_checks),
            "note": (
                "Missing context is reported explicitly; no confidence score is inferred."
                if missing_context
                else "Basic report context is present; this does not prove sensor accuracy."
            ),
        },
        "evidence_sources": {
            "current_telemetry": {
                "label": "machine_reading",
                "data": reading,
            },
            "health_and_risk": {
                "label": "deterministic_health_and_risk_assessment",
                "health": health,
                "maintenance_risk": risk,
                "anomaly": anomaly,
            },
            "rule_based_findings": {
                "label": "deterministic_root_cause_rules",
                "status": root_cause.get("status", "unknown"),
                "findings": rule_findings,
            },
            "verified_maintenance_history": {
                "label": verified.get("evidence_label", "human_verified_historical_context"),
                "evidence_count": verified.get("evidence_count", 0),
                "matching_verified_cases": verified.get("matching_verified_cases", 0),
                "records": verified_records,
                "interpretation": verified.get(
                    "interpretation",
                    "Historical records are context only and do not prove the current cause.",
                ),
            },
        },
        "recommended_checks": recommended_checks,
        "limitations": [
            "Rule-based findings are potential contributing causes, not confirmed diagnoses.",
            "Historical repairs may inform inspection but do not prove the current fault cause.",
            "This report does not establish real-machine model accuracy or production safety.",
            "A present numeric measurement does not establish that the sensor is calibrated or healthy.",
        ],
        "human_review_required": True,
        "automatic_diagnosis_performed": False,
        "model_updated": False,
        "control_write_performed": False,
        "plc_write_performed": False,
    }
