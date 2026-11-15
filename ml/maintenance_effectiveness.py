"""Descriptive effectiveness summaries from human-verified maintenance records.

Metrics describe recorded repair outcomes and repeat fault observations. They do
not establish that a repair caused a machine condition to improve or recur.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def summarize_maintenance_effectiveness(
    outcomes: list[dict[str, Any]],
    machine_id: str | None = None,
    fault_code: str | None = None,
) -> dict[str, Any]:
    """Summarize verified cases by machine and fault code, newest first."""
    if machine_id is not None and (
        not isinstance(machine_id, str) or not machine_id.strip()
    ):
        return {"status": "rejected", "error": "machine_id cannot be empty"}
    if fault_code is not None and (
        not isinstance(fault_code, str) or not fault_code.strip()
    ):
        return {"status": "rejected", "error": "fault_code cannot be empty"}

    normalized_machine = machine_id.strip() if machine_id is not None else None
    normalized_fault = fault_code.strip().upper() if fault_code is not None else None
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for outcome in outcomes:
        if not isinstance(outcome, dict) or outcome.get("verified") not in (True, 1):
            continue
        current_machine = str(outcome.get("machine_id", "")).strip()
        current_fault = str(outcome.get("fault_code", "")).strip().upper()
        if not current_machine or not current_fault:
            continue
        if normalized_machine is not None and current_machine != normalized_machine:
            continue
        if normalized_fault is not None and current_fault != normalized_fault:
            continue
        parsed = _parse_timestamp(outcome.get("event_timestamp"))
        if parsed is None:
            continue
        groups[(current_machine, current_fault)].append({
            "outcome_id": outcome.get("outcome_id"),
            "event_timestamp": parsed.isoformat(),
            "_parsed_timestamp": parsed,
            "cause": str(outcome.get("cause", "")).strip() or None,
            "repair_action": str(outcome.get("repair_action", "")).strip() or None,
            "repair_successful": outcome.get("repair_successful") in (True, 1),
            "before_evidence": outcome.get("before_evidence"),
            "after_evidence": outcome.get("after_evidence"),
            "verified_by": outcome.get("verified_by"),
            "verification_method": outcome.get("verification_method"),
            "verification_result": outcome.get("verification_result"),
        })

    summaries = []
    total_cases = 0
    total_successes = 0
    for (current_machine, current_fault), cases in groups.items():
        cases.sort(key=lambda item: item["_parsed_timestamp"])
        count = len(cases)
        successes = sum(item["repair_successful"] for item in cases)
        timestamps = [item["_parsed_timestamp"] for item in cases]
        intervals = [
            round((timestamps[index] - timestamps[index - 1]).total_seconds() / 86400, 2)
            for index in range(1, len(timestamps))
        ]
        evidence_complete = sum(
            bool(item["before_evidence"] and item["after_evidence"])
            for item in cases
        )
        public_cases = [
            {key: value for key, value in item.items() if key != "_parsed_timestamp"}
            for item in reversed(cases)
        ]
        summaries.append({
            "machine_id": current_machine,
            "fault_code": current_fault,
            "verified_cases": count,
            "successful_repairs": successes,
            "unsuccessful_repairs": count - successes,
            "recorded_success_rate": round(successes / count, 3),
            "recurrence_observed": count > 1,
            "repeat_intervals_days": intervals,
            "latest_event": cases[-1]["event_timestamp"],
            "causes_recorded": sorted({item["cause"] for item in cases if item["cause"]}),
            "before_after_evidence_cases": evidence_complete,
            "cases_with_before_after_evidence": evidence_complete,
            "cases": public_cases,
            "evidence_status": "human_verified",
        })
        total_cases += count
        total_successes += successes

    summaries.sort(
        key=lambda item: (item["verified_cases"], item["latest_event"]),
        reverse=True,
    )
    return {
        "status": "ok",
        "machine_id": normalized_machine,
        "fault_code": normalized_fault,
        "groups": len(summaries),
        "verified_cases": total_cases,
        "successful_repairs": total_successes,
        "recorded_success_rate": round(total_successes / total_cases, 3) if total_cases else None,
        "summaries": summaries,
        "interpretation": (
            "Success rates and repeat intervals describe recorded, human-verified cases only. "
            "A repeated fault after a repair is a temporal observation, not proof that the "
            "repair failed or caused recurrence. Review machine conditions and evidence."
        ),
        "unverified_records_included": False,
        "causal_effectiveness_claimed": False,
        "automatic_diagnosis_performed": False,
        "model_updated": False,
        "control_write_performed": False,
        "plc_write_performed": False,
    }
