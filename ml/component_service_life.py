"""Descriptive service-life analytics from recorded component lifecycle events."""
from __future__ import annotations

from datetime import datetime
from statistics import median
from typing import Any


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed


def summarize_component_service_life(
    events: list[dict[str, Any]],
    machine_id: str | None = None,
    part_number: str | None = None,
) -> dict[str, Any]:
    """Pair install/remove events and summarize observed usage; never extrapolate."""
    if not isinstance(events, list):
        return {"status": "rejected", "error": "events must be a list"}
    normalized_machine = str(machine_id).strip() if machine_id is not None else None
    normalized_part = str(part_number).strip().casefold() if part_number is not None else None
    if machine_id is not None and not normalized_machine:
        return {"status": "rejected", "error": "machine_id cannot be empty"}
    if part_number is not None and not normalized_part:
        return {"status": "rejected", "error": "part_number cannot be empty"}

    ordered = sorted(
        [item for item in events if isinstance(item, dict)],
        key=lambda item: (str(item.get("event_timestamp", "")), str(item.get("event_id", ""))),
    )
    active: dict[tuple[str, str], dict[str, Any]] = {}
    completed: list[dict[str, Any]] = []
    for event in ordered:
        event_machine = str(event.get("machine_id", "")).strip()
        component_id = str(event.get("component_id", "")).strip()
        if not event_machine or not component_id:
            continue
        if normalized_machine and event_machine != normalized_machine:
            continue
        key = (event_machine, component_id)
        event_type = event.get("event_type")
        if event_type == "install":
            active[key] = event
        elif event_type == "remove":
            install = active.pop(key, None)
            if install is None:
                continue
            install_time = _parse_time(install.get("event_timestamp"))
            remove_time = _parse_time(event.get("event_timestamp"))
            if install_time is None or remove_time is None or remove_time < install_time:
                continue
            try:
                runtime_used = float(event["runtime_hours"]) - float(install["runtime_hours"])
                cycles_used = float(event["production_cycles"]) - float(install["production_cycles"])
            except (KeyError, TypeError, ValueError):
                continue
            if runtime_used < 0 or cycles_used < 0:
                continue
            part = str(install.get("part_number", "")).strip()
            if normalized_part and part.casefold() != normalized_part:
                continue
            completed.append({
                "machine_id": event_machine,
                "component_id": component_id,
                "part_number": part or None,
                "part_name": install.get("part_name"),
                "installed_at": install.get("event_timestamp"),
                "removed_at": event.get("event_timestamp"),
                "runtime_hours_observed": round(runtime_used, 2),
                "production_cycles_observed": round(cycles_used, 2),
                "calendar_days_observed": (remove_time - install_time).total_seconds() / 86400,
                "removal_reason": event.get("removal_reason"),
                "maintenance_action": event.get("maintenance_action"),
                "install_event_id": install.get("event_id"),
                "remove_event_id": event.get("event_id"),
            })

    groups: dict[str, list[dict[str, Any]]] = {}
    for item in completed:
        group = str(item.get("part_number") or "UNSPECIFIED")
        groups.setdefault(group, []).append(item)

    summaries = []
    for part, cases in sorted(groups.items()):
        runtimes = [case["runtime_hours_observed"] for case in cases]
        cycles = [case["production_cycles_observed"] for case in cases]
        days = [case["calendar_days_observed"] for case in cases]
        summaries.append({
            "part_number": part,
            "completed_lifecycle_count": len(cases),
            "average_runtime_hours_observed": round(sum(runtimes) / len(runtimes), 2),
            "median_runtime_hours_observed": round(median(runtimes), 2),
            "average_production_cycles_observed": round(sum(cycles) / len(cycles), 2),
            "median_calendar_days_observed": round(median(days), 2),
            "evidence_label": "recorded_completed_lifecycles",
        })

    return {
        "status": "ok",
        "machine_id": normalized_machine,
        "part_number_filter": part_number,
        "completed_lifecycle_count": len(completed),
        "active_installation_count": len(active),
        "completed_lifecycles": sorted(
            completed, key=lambda item: (item["removed_at"], item["component_id"]), reverse=True
        ),
        "part_summaries": summaries,
        "interpretation": (
            "Statistics describe only recorded completed installation-to-removal intervals. "
            "Removal does not necessarily mean component failure; usage is not a rated-life limit."
        ),
        "failure_prediction_performed": False,
        "remaining_useful_life_estimated": False,
        "control_write_performed": False,
        "plc_write_performed": False,
    }
