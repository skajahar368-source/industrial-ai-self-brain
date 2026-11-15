"""Tests for the combined machine maintenance timeline."""
from ml.maintenance_timeline import build_maintenance_timeline


def report(report_id, timestamp, machine_id="M-1"):
    return {
        "status": "ok",
        "report_id": report_id,
        "machine_id": machine_id,
        "archived_at_utc": timestamp,
        "summary": {
            "fault_code": "HIGH_VIBRATION",
            "health_status": "warning",
            "maintenance_risk_level": "medium",
            "maintenance_risk_score": 55,
            "anomaly_flagged": True,
        },
        "evidence_quality": {"status": "available"},
    }


def outcome(outcome_id, timestamp, machine_id="M-1", verified=True):
    return {
        "outcome_id": outcome_id,
        "event_timestamp": timestamp,
        "machine_id": machine_id,
        "fault_code": "HIGH_VIBRATION",
        "cause": "bearing wear",
        "repair_action": "replace bearing",
        "repair_successful": True,
        "verified": verified,
        "verified_by": "maintenance-engineer",
        "verification_method": "post-repair vibration measurement",
        "verification_result": "vibration returned to baseline",
    }


def test_timeline_merges_events_newest_first_and_keeps_evidence_labels():
    result = build_maintenance_timeline(
        [report("r2", "2026-11-02T10:00:00+00:00"), report("r1", "2026-11-01T10:00:00+00:00")],
        [outcome("m1", "2026-11-01T12:00:00+00:00")],
        "M-1",
    )
    assert result["status"] == "ok"
    assert [event["event_id"] for event in result["events"]] == ["r2", "m1", "r1"]
    assert result["event_counts"] == {"investigation_reports": 2, "verified_maintenance": 1}
    assert result["events"][1]["evidence_label"] == "human_verified_maintenance_record"
    assert result["human_review_required"] is True
    assert result["automatic_diagnosis_performed"] is False
    assert result["model_updated"] is False
    assert result["control_write_performed"] is False


def test_timeline_excludes_other_machines_unverified_and_malformed_events():
    result = build_maintenance_timeline(
        [report("other", "2026-11-02T10:00:00Z", "M-2"), {"status": "error"}],
        [outcome("unverified", "2026-11-01T10:00:00Z", verified=False),
         outcome("other", "2026-11-01T10:00:00Z", "M-2")],
        "M-1",
    )
    assert result["total_events"] == 0
    assert result["events"] == []


def test_timeline_validates_machine_and_limit():
    assert build_maintenance_timeline([], [], " ")["status"] == "rejected"
    assert build_maintenance_timeline([], [], "M-1", 0)["status"] == "rejected"
    assert build_maintenance_timeline([], [], "M-1", True)["status"] == "rejected"


def test_timeline_limit_is_applied_after_chronological_sort():
    result = build_maintenance_timeline(
        [report("older", "2026-11-01T10:00:00Z"), report("newer", "2026-11-03T10:00:00Z")],
        [], "M-1", limit=1,
    )
    assert result["returned_events"] == 1
    assert result["events"][0]["event_id"] == "newer"
