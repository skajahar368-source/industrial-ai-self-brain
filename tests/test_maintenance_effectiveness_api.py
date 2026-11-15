"""API tests for verified maintenance effectiveness review."""
from app.api import routes
from ml.verified_maintenance_learning import VerifiedMaintenanceLearning


def _outcome(timestamp, successful, action):
    return {
        "event_timestamp": timestamp,
        "machine_id": "M-EFFECT",
        "fault_code": "HIGH_VIBRATION",
        "cause": "bearing wear",
        "repair_action": action,
        "repair_successful": successful,
        "verified": True,
        "verified_by": "maintenance-engineer",
        "verification_method": "post-repair vibration measurement",
        "verification_result": "vibration measured",
        "before_evidence": "vibration high",
        "after_evidence": "vibration changed",
    }


def test_effectiveness_endpoint_summarizes_persisted_verified_records(monkeypatch, tmp_path):
    database = tmp_path / "verified.sqlite3"
    monkeypatch.setattr(routes, "VERIFIED_MAINTENANCE_DB", database)
    store = VerifiedMaintenanceLearning(database)
    assert store.record(_outcome("2026-11-01T09:00:00Z", True, "replace bearing"))["status"] == "recorded"
    assert store.record(_outcome("2026-11-04T09:00:00Z", False, "inspect mounting"))["status"] == "recorded"
    store.close()

    result = routes.verified_maintenance_effectiveness(
        machine_id="M-EFFECT", fault_code="high_vibration", limit=10
    )

    assert result["status"] == "ok"
    assert result["verified_cases"] == 2
    assert result["recorded_success_rate"] == 0.5
    assert result["summaries"][0]["repeat_intervals_days"] == [3.0]
    assert result["plc_write_performed"] is False


def test_effectiveness_endpoint_rejects_invalid_limit():
    assert routes.verified_maintenance_effectiveness(limit=101)["status"] == "rejected"
