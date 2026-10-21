"""API-level tests for verified maintenance evidence persistence and boundaries."""

from app.api import routes


def valid_outcome(**overrides):
    payload = {
        "event_timestamp": "2026-10-21T10:00:00Z",
        "machine_id": "M-API-TEST",
        "fault_code": "HIGH_VIBRATION",
        "cause": "bearing wear",
        "repair_action": "replace bearing",
        "repair_successful": True,
        "verified": True,
        "verified_by": "maintenance-engineer",
        "verification_method": "post-repair vibration measurement",
        "verification_result": "vibration returned to baseline",
    }
    payload.update(overrides)
    return payload


def test_maintenance_learning_api_persists_between_requests(monkeypatch, tmp_path):
    monkeypatch.setattr(
        routes, "VERIFIED_MAINTENANCE_DB", tmp_path / "api-learning.sqlite3"
    )

    recorded = routes.record_verified_maintenance_outcome(valid_outcome())
    assert recorded["status"] == "recorded"
    assert recorded["model_updated"] is False
    assert recorded["control_write_performed"] is False

    # The route creates a fresh store for each request; this checks disk persistence.
    result = routes.verified_maintenance_insights(
        machine_id="M-API-TEST", fault_code="high_vibration"
    )
    assert result["status"] == "ok"
    assert result["count"] == 1
    insight = result["insights"][0]
    assert insight["fault_code"] == "HIGH_VIBRATION"
    assert insight["verified_cases"] == 1
    assert insight["success_rate"] == 1.0
    assert insight["recommendation_type"] == "historical_evidence_only"
    assert result["unverified_ai_suggestions_included"] is False
    assert result["model_updated"] is False
    assert result["control_write_performed"] is False


def test_maintenance_learning_api_blocks_unverified_outcome(monkeypatch, tmp_path):
    monkeypatch.setattr(
        routes, "VERIFIED_MAINTENANCE_DB", tmp_path / "api-learning.sqlite3"
    )

    result = routes.record_verified_maintenance_outcome(
        valid_outcome(verified=False)
    )
    assert result["status"] == "blocked"

    insights = routes.verified_maintenance_insights(machine_id="M-API-TEST")
    assert insights["count"] == 0


def test_maintenance_learning_api_filters_by_machine(monkeypatch, tmp_path):
    monkeypatch.setattr(
        routes, "VERIFIED_MAINTENANCE_DB", tmp_path / "api-learning.sqlite3"
    )
    routes.record_verified_maintenance_outcome(valid_outcome())
    routes.record_verified_maintenance_outcome(
        valid_outcome(machine_id="M-OTHER", fault_code="HIGH_TEMPERATURE")
    )

    result = routes.verified_maintenance_insights(machine_id="M-API-TEST")
    assert result["count"] == 1
    assert result["insights"][0]["machine_id"] == "M-API-TEST"
