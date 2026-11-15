"""Chronological view of archived reports and verified maintenance events.

This module joins recorded events for a machine. It does not infer that a repair
caused a later condition change, diagnose faults, retrain models, or control PLCs.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def build_maintenance_timeline(
    reports: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
    machine_id: str,
    limit: int = 100,
) -> dict[str, Any]:
    """Merge report snapshots and human-verified repairs, newest event first."""
    if not isinstance(machine_id, str) or not machine_id.strip():
        return {"status": "rejected", "error": "machine_id is required"}
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        return {"status": "rejected", "error": "limit must be an integer between 1 and 100"}

    machine_id = machine_id.strip()
    events: list[dict[str, Any]] = []
    for report in reports:
        if not isinstance(report, dict) or report.get("status") != "ok":
            continue
        if str(report.get("machine_id", "")).strip() != machine_id:
            continue
        summary = report.get("summary")
        if not isinstance(summary, dict):
            continue
        # The summary timestamp is when the machine reading was observed.
        # archived_at_utc is only the storage time and may be much later.
        event_time = summary.get("timestamp") or report.get("archived_at_utc")
        parsed = _timestamp(event_time)
        if parsed is None:
            continue
        events.append({
            "event_id": report.get("report_id"),
            "event_type": "investigation_report",
            "event_timestamp": parsed.isoformat(),
            "machine_id": machine_id,
            "fault_code": summary.get("fault_code"),
            "health_status": summary.get("health_status"),
            "maintenance_risk_level": summary.get("maintenance_risk_level"),
            "maintenance_risk_score": summary.get("maintenance_risk_score"),
            "anomaly_flagged": summary.get("anomaly_flagged"),
            "evidence_quality": (
                report.get("evidence_quality", {}).get("status")
                if isinstance(report.get("evidence_quality"), dict) else "unknown"
            ),
            "evidence_label": "archived_ai_assisted_investigation_report",
        })

    for outcome in outcomes:
        if not isinstance(outcome, dict) or outcome.get("verified") not in (True, 1):
            continue
        if str(outcome.get("machine_id", "")).strip() != machine_id:
            continue
        parsed = _timestamp(outcome.get("event_timestamp"))
        if parsed is None:
            continue
        events.append({
            "event_id": outcome.get("outcome_id"),
            "event_type": "verified_maintenance",
            "event_timestamp": parsed.isoformat(),
            "machine_id": machine_id,
            "fault_code": outcome.get("fault_code"),
            "cause": outcome.get("cause"),
            "repair_action": outcome.get("repair_action"),
            "repair_successful": bool(outcome.get("repair_successful")),
            "verified_by": outcome.get("verified_by"),
            "verification_method": outcome.get("verification_method"),
            "verification_result": outcome.get("verification_result"),
            "before_evidence": outcome.get("before_evidence"),
            "after_evidence": outcome.get("after_evidence"),
            "evidence_label": "human_verified_maintenance_record",
        })

    events.sort(key=lambda item: _timestamp(item["event_timestamp"]), reverse=True)
    selected = events[:limit]
    return {
        "status": "ok",
        "machine_id": machine_id,
        "total_events": len(events),
        "returned_events": len(selected),
        "event_counts": {
            "investigation_reports": sum(e["event_type"] == "investigation_report" for e in selected),
            "verified_maintenance": sum(e["event_type"] == "verified_maintenance" for e in selected),
        },
        "events": selected,
        "interpretation": (
            "Events are ordered by their recorded timestamps. A repair and a later "
            "report appearing near each other does not prove the repair caused a change."
        ),
        "human_review_required": True,
        "automatic_diagnosis_performed": False,
        "model_updated": False,
        "control_write_performed": False,
        "plc_write_performed": False,
    }
