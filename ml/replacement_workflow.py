from __future__ import annotations

from typing import Any

EARLY_REPLACEMENT_REASONS = {
    "misalignment": "Part or shaft alignment is outside the required condition.",
    "cleaning_issue": "Dirt, dust, contamination, or blocked airflow caused abnormal operation.",
    "lubrication_issue": "Insufficient, incorrect, or degraded lubrication contributed to wear.",
    "overheating": "Excessive temperature or thermal stress caused degradation.",
    "excessive_vibration": "Abnormal vibration or mechanical imbalance caused degradation.",
    "abnormal_pressure": "Pressure outside the normal operating range caused damage.",
    "electrical_fault": "Electrical fault, overload, short circuit, or unstable supply caused damage.",
    "overload": "The component experienced load beyond its intended operating condition.",
    "wear_and_tear": "Normal physical wear was observed before rated life was reached.",
    "foreign_material": "A foreign object or contamination damaged the component.",
    "installation_error": "Incorrect installation, torque, seating, or assembly contributed to failure.",
    "material_defect": "A suspected material or manufacturing defect was found.",
    "operator_or_process_issue": "Operating or process conditions contributed to the failure.",
    "unknown": "Cause is not yet confirmed; further investigation is required.",
}

REQUIRED_EVIDENCE = {
    "visual_inspection",
    "measurement",
    "sensor_data",
    "maintenance_history",
    "operator_report",
    "other",
}


def validate_early_replacement(payload: dict[str, Any]) -> dict[str, Any]:
    """Require a reason, evidence, corrective action, and verification for early replacement."""
    reason = payload.get("reason_code")
    evidence = payload.get("evidence_type")
    corrective_action = str(payload.get("corrective_action", "")).strip()
    verification = str(payload.get("verification_result", "")).strip()
    replacement_approved = bool(payload.get("replacement_approved", False))

    errors = []
    if reason not in EARLY_REPLACEMENT_REASONS:
        errors.append("A valid reason_code is required.")
    if evidence not in REQUIRED_EVIDENCE:
        errors.append("A valid evidence_type is required.")
    if not corrective_action:
        errors.append("corrective_action is required.")
    if not verification:
        errors.append("verification_result is required.")
    if not replacement_approved:
        errors.append("replacement_approved must be true before an early replacement can be closed.")

    if errors:
        return {"status": "blocked", "errors": errors}

    return {
        "status": "approved_for_recording",
        "reason_code": reason,
        "reason_description": EARLY_REPLACEMENT_REASONS[reason],
        "evidence_type": evidence,
        "corrective_action": corrective_action,
        "verification_result": verification,
        "replacement_approved": True,
    }
