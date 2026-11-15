"""Read-only machine-wide maintenance investigation context.

This module combines independently labelled source snapshots. It deliberately
does not infer causality, generate a diagnosis, or issue machine-control writes.
"""
from __future__ import annotations

from typing import Any


def build_machine_maintenance_context(
    machine_id: str,
    telemetry_records: list[dict[str, Any]],
    alarm_snapshot: dict[str, Any],
    maintenance_timeline: dict[str, Any],
    maintenance_effectiveness: dict[str, Any],
    component_history: dict[str, Any],
    component_service_life: dict[str, Any],
    *,
    telemetry_quality: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble current telemetry and historical evidence for one exact machine."""
    if not isinstance(machine_id, str) or not machine_id.strip():
        return {"status": "rejected", "error": "machine_id is required"}
    if not isinstance(telemetry_records, list):
        return {"status": "rejected", "error": "telemetry_records must be a list"}

    machine_id = machine_id.strip()
    telemetry = [
        item for item in telemetry_records
        if isinstance(item, dict) and str(item.get("machine_id", "")).strip() == machine_id
    ]
    telemetry.sort(key=lambda item: str(item.get("timestamp", "")), reverse=True)

    alarms = alarm_snapshot.get("alarms", []) if isinstance(alarm_snapshot, dict) else []
    alarms = [
        item for item in alarms
        if isinstance(item, dict) and str(item.get("machine_id", "")).strip() == machine_id
    ]
    active_alarms = [item for item in alarms if item.get("active") is True]

    timeline_events = (
        maintenance_timeline.get("events", [])
        if isinstance(maintenance_timeline, dict) else []
    )
    timeline_events = [
        item for item in timeline_events
        if isinstance(item, dict) and str(item.get("machine_id", "")).strip() == machine_id
    ]

    lifecycle_events = (
        component_history.get("events", [])
        if isinstance(component_history, dict) else []
    )
    lifecycle_events = [
        item for item in lifecycle_events
        if isinstance(item, dict) and str(item.get("machine_id", "")).strip() == machine_id
    ]
    active_components = (
        component_history.get("active_components", [])
        if isinstance(component_history, dict) else []
    )
    active_components = [
        item for item in active_components
        if isinstance(item, dict) and str(item.get("machine_id", "")).strip() == machine_id
    ]

    completed_lifecycles = (
        component_service_life.get("completed_lifecycles", [])
        if isinstance(component_service_life, dict) else []
    )
    completed_lifecycles = [
        item for item in completed_lifecycles
        if isinstance(item, dict) and str(item.get("machine_id", "")).strip() == machine_id
    ]

    effectiveness_groups = (
        maintenance_effectiveness.get("summaries", [])
        if isinstance(maintenance_effectiveness, dict) else []
    )
    effectiveness_groups = [
        item for item in effectiveness_groups
        if isinstance(item, dict) and str(item.get("machine_id", "")).strip() == machine_id
    ]
    verified_case_count = sum(
        int(item.get("verified_cases", 0) or 0) for item in effectiveness_groups
    )
    quality_summary = telemetry_quality if isinstance(telemetry_quality, dict) else {
        "status": "insufficient_data", "quality": "unknown", "issues": [], "issue_count": 0
    }

    return {
        "status": "ok",
        "machine_id": machine_id,
        "view_type": "read_only_machine_maintenance_context",
        "telemetry_data_quality": {
            **quality_summary,
            "source_label": "deterministic_telemetry_quality_checks",
            "interpretation": "Flags indicate data-quality concerns, not machine faults. Review raw readings and sensor condition.",
        },
        "current_snapshot": {
            "latest_telemetry": telemetry[0] if telemetry else None,
            "telemetry_records_returned": len(telemetry),
            "telemetry_source_label": "recorded_machine_telemetry",
            "active_alarms": active_alarms,
            "alarm_history_count": len(alarms),
            "alarm_source_label": "observed_plc_alarm_history",
        },
        "historical_evidence": {
            "maintenance_timeline": {
                "events": timeline_events,
                "event_count": len(timeline_events),
                "source_status": maintenance_timeline.get("status", "unavailable")
                if isinstance(maintenance_timeline, dict) else "unavailable",
                "source_label": "archived_reports_and_human_verified_repairs",
            },
            "maintenance_effectiveness": {
                "summaries": effectiveness_groups,
                "verified_case_count": verified_case_count,
                "source_status": maintenance_effectiveness.get("status", "unavailable")
                if isinstance(maintenance_effectiveness, dict) else "unavailable",
                "source_label": "human_verified_maintenance_records_only",
            },
            "component_lifecycle": {
                "events": lifecycle_events,
                "active_components": active_components,
                "event_count": len(lifecycle_events),
                "active_component_count": len(active_components),
                "source_status": component_history.get("status", "unavailable")
                if isinstance(component_history, dict) else "unavailable",
                "source_label": "append_only_component_lifecycle_ledger",
            },
            "component_service_life": {
                "completed_lifecycles": completed_lifecycles,
                "part_summaries": component_service_life.get("part_summaries", [])
                if isinstance(component_service_life, dict) else [],
                "completed_lifecycle_count": len(completed_lifecycles),
                "source_status": component_service_life.get("status", "unavailable")
                if isinstance(component_service_life, dict) else "unavailable",
                "source_label": "recorded_completed_installation_to_removal_intervals",
            },
        },
        "evidence_coverage": {
            "telemetry_available": bool(telemetry),
            "telemetry_quality_degraded": quality_summary.get("quality") == "degraded",
            "alarm_history_available": bool(alarms),
            "maintenance_timeline_available": bool(timeline_events),
            "verified_maintenance_available": verified_case_count > 0,
            "component_lifecycle_available": bool(lifecycle_events),
            "completed_component_lifecycles_available": bool(completed_lifecycles),
            "missing_sources_are_not_evidence_of_normal_condition": True,
        },
        "interpretation": (
            "Current telemetry and observed alarms are separated from historical records. "
            "Historical proximity does not establish cause or repair effectiveness. "
            "Only explicitly human-verified maintenance records are counted as verified cases. "
            "A component removal does not necessarily mean failure. Review source timestamps, "
            "data quality, and physical evidence before taking maintenance action."
        ),
        "automatic_diagnosis_performed": False,
        "causal_relationship_inferred": False,
        "model_updated": False,
        "control_write_performed": False,
        "plc_write_performed": False,
        "human_review_required": True,
    }
