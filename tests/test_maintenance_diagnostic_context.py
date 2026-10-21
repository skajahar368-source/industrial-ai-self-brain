"""Tests for evidence-grounded diagnostic context from verified maintenance history."""

from app.api import routes


def outcome(**overrides):
    payload = {
        "event_timestamp": "2026-10-21T10:00:00Z",
        "machine_id": "M-CONTEXT",
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


def test_diagnostic_context_returns_only_matching_verified_evidence(monkeypatch, tmp_path):
    monkeypatch.setattr(
        routes, "VERIFIED_MAINTENANCE_DB", tmp_path / "context.sqlite3"
    )
    assert routes.record_verified_maintenance_outcome(outcome())["status"] == "recorded"
    assert routes.record_verified_maintenance_outcome(
        outcome(
            event_timestamp="2026-10-21T11:00:00Z",
            cause="shaft misalignment",
            repair_action="align shaft",
            repair_successful=False,
        )
    )["status"] == "recorded"

    result = routes.verified_maintenance_diagnostic_context({
        "machine_id": "M-CONTEXT",
        "fault_code": "high_vibration",
        "causes": ["Bearing Wear"],
    })

    assert result["status"] == "ok"
    assert result["evidence_count"] == 1
    assert result["matching_verified_cases"] == 1
    assert result["evidence"][0]["cause"] == "bearing wear"
    assert result["evidence_label"] == "human_verified_historical_context"
    assert result["automatic_diagnosis_performed"] is False
    assert result["model_updated"] is False
    assert result["control_write_performed"] is False


def test_diagnostic_context_reports_missing_evidence_without_guessing(monkeypatch, tmp_path):
    monkeypatch.setattr(
        routes, "VERIFIED_MAINTENANCE_DB", tmp_path / "context.sqlite3"
    )
    result = routes.verified_maintenance_diagnostic_context({
        "machine_id": "M-UNKNOWN",
        "fault_code": "HIGH_TEMPERATURE",
    })

    assert result["status"] == "ok"
    assert result["evidence_count"] == 0
    assert result["matching_verified_cases"] == 0
    assert "No matching verified maintenance history" in result["interpretation"]
    assert result["automatic_diagnosis_performed"] is False


def test_diagnostic_context_validates_required_fields_and_causes(monkeypatch, tmp_path):
    monkeypatch.setattr(
        routes, "VERIFIED_MAINTENANCE_DB", tmp_path / "context.sqlite3"
    )
    assert routes.verified_maintenance_diagnostic_context({
        "fault_code": "HIGH_VIBRATION",
    })["status"] == "blocked"
    assert routes.verified_maintenance_diagnostic_context({
        "machine_id": "M-CONTEXT",
    })["status"] == "blocked"
    assert routes.verified_maintenance_diagnostic_context({
        "machine_id": "M-CONTEXT",
        "fault_code": "HIGH_VIBRATION",
        "causes": "bearing wear",
    })["status"] == "blocked"
