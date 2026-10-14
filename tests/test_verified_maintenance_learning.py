"""Tests for verified maintenance learning and evidence separation."""
from ml.verified_maintenance_learning import VerifiedMaintenanceLearning


def valid_outcome(**overrides):
    payload = {
        "event_timestamp": "2026-10-14T10:00:00Z",
        "machine_id": "M-TEST",
        "fault_code": "HIGH_VIBRATION",
        "cause": "bearing wear",
        "repair_action": "replace bearing",
        "repair_successful": True,
        "verified": True,
        "verified_by": "maintenance-engineer",
        "verification_method": "post-repair vibration measurement",
        "verification_result": "vibration returned to baseline",
        "before_evidence": "vibration high",
        "after_evidence": "vibration normal",
    }
    payload.update(overrides)
    return payload


def test_verified_outcome_persists_and_builds_insight(tmp_path):
    database = tmp_path / "learning.sqlite3"
    store = VerifiedMaintenanceLearning(database)
    result = store.record(valid_outcome())
    assert result["status"] == "recorded"
    assert result["model_updated"] is False
    store.close()

    restarted = VerifiedMaintenanceLearning(database)
    insights = restarted.insights(machine_id="M-TEST")
    assert insights["count"] == 1
    pattern = insights["insights"][0]
    assert pattern["verified_cases"] == 1
    assert pattern["success_rate"] == 1.0
    assert pattern["evidence_status"] == "human_verified"
    assert insights["unverified_ai_suggestions_included"] is False
    assert insights["control_write_performed"] is False
    restarted.close()


def test_unverified_outcome_is_blocked(tmp_path):
    store = VerifiedMaintenanceLearning(tmp_path / "learning.sqlite3")
    result = store.record(valid_outcome(verified=False))
    assert result["status"] == "blocked"
    assert store.insights()["count"] == 0
    store.close()


def test_required_verification_fields_are_enforced(tmp_path):
    store = VerifiedMaintenanceLearning(tmp_path / "learning.sqlite3")
    result = store.record(valid_outcome(verification_result=""))
    assert result["status"] == "blocked"
    assert store.insights()["count"] == 0
    store.close()


def test_success_rate_uses_only_verified_records(tmp_path):
    store = VerifiedMaintenanceLearning(tmp_path / "learning.sqlite3")
    assert store.record(valid_outcome())["status"] == "recorded"
    assert store.record(valid_outcome(
        event_timestamp="2026-10-14T11:00:00Z",
        repair_successful=False,
        repair_action="inspect alignment",
    ))["status"] == "recorded"
    result = store.insights(fault_code="high_vibration")
    assert result["count"] == 1
    assert result["insights"][0]["verified_cases"] == 2
    assert result["insights"][0]["successful_repairs"] == 1
    assert result["insights"][0]["success_rate"] == 0.5
    store.close()


def test_invalid_timestamp_is_blocked(tmp_path):
    store = VerifiedMaintenanceLearning(tmp_path / "learning.sqlite3")
    result = store.record(valid_outcome(event_timestamp="yesterday"))
    assert result["status"] == "blocked"
    store.close()
