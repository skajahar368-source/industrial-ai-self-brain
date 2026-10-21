"""Deterministic comparisons of archived maintenance investigation reports.

This module summarizes changes in recorded reports; it does not diagnose faults,
infer causation, update models, or control machinery.
"""
from __future__ import annotations

from typing import Any


def _summary(report: dict[str, Any]) -> dict[str, Any]:
    value = report.get("summary")
    return value if isinstance(value, dict) else {}


def _score(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def summarize_report_trends(reports_newest_first: list[dict[str, Any]], machine_id: str) -> dict[str, Any]:
    """Compare archived reports newest-first and report only observable changes."""
    if not isinstance(machine_id, str) or not machine_id.strip():
        return {"status": "rejected", "error": "machine_id is required"}

    valid = [
        report for report in reports_newest_first
        if isinstance(report, dict)
        and report.get("status") == "ok"
        and str(report.get("machine_id", "")).strip() == machine_id.strip()
        and isinstance(report.get("summary"), dict)
    ]
    if not valid:
        return {
            "status": "not_found",
            "machine_id": machine_id.strip(),
            "report_count": 0,
            "message": "No successful archived reports were found for this machine.",
            "human_review_required": True,
            "automatic_diagnosis_performed": False,
            "model_updated": False,
            "control_write_performed": False,
        }

    # Input is newest-first. Compare oldest available to newest available.
    newest = valid[0]
    oldest = valid[-1]
    newest_summary = _summary(newest)
    oldest_summary = _summary(oldest)
    newest_score = _score(newest_summary.get("maintenance_risk_score"))
    oldest_score = _score(oldest_summary.get("maintenance_risk_score"))
    score_delta = (
        round(newest_score - oldest_score, 3)
        if newest_score is not None and oldest_score is not None
        else None
    )

    health_values = [str(_summary(report).get("health_status") or "unknown") for report in reversed(valid)]
    risk_values = [str(_summary(report).get("maintenance_risk_level") or "unknown") for report in reversed(valid)]
    fault_values = [str(_summary(report).get("fault_code") or "unknown") for report in reversed(valid)]
    anomaly_values = [ _summary(report).get("anomaly_flagged") for report in reversed(valid) ]

    distinct_faults = list(dict.fromkeys(fault_values))
    if score_delta is None:
        score_direction = "not_comparable"
    elif score_delta > 0:
        score_direction = "increased"
    elif score_delta < 0:
        score_direction = "decreased"
    else:
        score_direction = "unchanged"

    report_summaries = []
    for report in reversed(valid):
        summary = _summary(report)
        report_summaries.append({
            "report_id": report.get("report_id"),
            "archived_at_utc": report.get("archived_at_utc"),
            "reading_timestamp": summary.get("timestamp"),
            "health_status": summary.get("health_status", "unknown"),
            "maintenance_risk_level": summary.get("maintenance_risk_level", "unknown"),
            "maintenance_risk_score": _score(summary.get("maintenance_risk_score")),
            "fault_code": summary.get("fault_code"),
            "anomaly_flagged": summary.get("anomaly_flagged"),
            "evidence_quality": report.get("evidence_quality", {}).get("status")
            if isinstance(report.get("evidence_quality"), dict) else "unknown",
        })

    return {
        "status": "ok",
        "machine_id": machine_id.strip(),
        "report_count": len(valid),
        "comparison": {
            "from_report_id": oldest.get("report_id"),
            "to_report_id": newest.get("report_id"),
            "from_archived_at_utc": oldest.get("archived_at_utc"),
            "to_archived_at_utc": newest.get("archived_at_utc"),
            "health_status": {"from": health_values[0], "to": health_values[-1], "changed": health_values[0] != health_values[-1]},
            "maintenance_risk_level": {"from": risk_values[0], "to": risk_values[-1], "changed": risk_values[0] != risk_values[-1]},
            "maintenance_risk_score": {
                "from": oldest_score,
                "to": newest_score,
                "delta": score_delta,
                "direction": score_direction,
            },
            "fault_code": {"from": fault_values[0], "to": fault_values[-1], "changed": fault_values[0] != fault_values[-1]},
            "anomaly_flagged": {"from": anomaly_values[0], "to": anomaly_values[-1], "changed": anomaly_values[0] != anomaly_values[-1]},
            "distinct_fault_codes": distinct_faults,
        },
        "reports_chronological": report_summaries,
        "interpretation": "This is a comparison of archived report fields, not proof that the machine condition improved, worsened, or that one fault caused another. Missing values are not estimated.",
        "human_review_required": True,
        "automatic_diagnosis_performed": False,
        "model_updated": False,
        "control_write_performed": False,
        "plc_write_performed": False,
    }
