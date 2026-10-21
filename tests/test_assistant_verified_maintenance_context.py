"""V2.9 tests for verified maintenance evidence in assistant responses."""

from ml import industrial_assistant
from ml.verified_maintenance_learning import VerifiedMaintenanceLearning


def verified_outcome(**overrides):
    payload = {
        "event_timestamp": "2026-10-20T10:00:00Z",
        "machine_id": "M-001",
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


def test_assistant_includes_matching_verified_history_as_context(monkeypatch, tmp_path):
    db_path = tmp_path / "verified.sqlite3"
    monkeypatch.setenv("SELF_BRAIN_MAINTENANCE_DB", str(db_path))
    store = VerifiedMaintenanceLearning(db_path)
    assert store.record(verified_outcome())["status"] == "recorded"
    store.close()

    monkeypatch.setattr(
        industrial_assistant,
        "_latest_machine_reading",
        lambda machine_id: {
            "timestamp": "2026-10-21T10:00:00Z",
            "machine_id": machine_id,
            "temperature_c": 82.0,
            "pressure_bar": 56.0,
            "vibration_mm_s": 8.2,
            "cycle_count": 1500,
            "downtime_minutes": 4,
            "fault_code": "HIGH_VIBRATION",
        },
    )

    result = industrial_assistant.ask_industrial_assistant({
        "machine_id": "M-001",
        "question": "Why is this machine having a problem?",
    })

    evidence = result["evidence"]["verified_maintenance_context"]
    assert result["status"] == "ok"
    assert evidence["evidence_count"] == 1
    assert evidence["matching_verified_cases"] == 1
    assert evidence["evidence"][0]["cause"] == "bearing wear"
    assert evidence["evidence"][0]["evidence_status"] == "human_verified"
    assert evidence["automatic_diagnosis_performed"] is False
    assert evidence["model_updated"] is False
    assert evidence["control_write_performed"] is False
    assert "not a current diagnosis" in result["answer"]
    assert "bearing wear" in result["answer"]


def test_assistant_does_not_guess_when_verified_history_is_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("SELF_BRAIN_MAINTENANCE_DB", str(tmp_path / "empty.sqlite3"))
    monkeypatch.setattr(
        industrial_assistant,
        "_latest_machine_reading",
        lambda machine_id: {
            "timestamp": "2026-10-21T10:00:00Z",
            "machine_id": machine_id,
            "temperature_c": 65.0,
            "pressure_bar": 55.0,
            "vibration_mm_s": 3.0,
            "cycle_count": 1200,
            "downtime_minutes": 0,
            "fault_code": "HIGH_VIBRATION",
        },
    )

    result = industrial_assistant.ask_industrial_assistant({
        "machine_id": "M-001",
        "question": "What is the condition?",
    })

    evidence = result["evidence"]["verified_maintenance_context"]
    assert result["status"] == "ok"
    assert evidence["evidence_count"] == 0
    assert evidence["evidence"] == []
    assert "No matching verified maintenance history" in evidence["interpretation"]
    assert evidence["automatic_diagnosis_performed"] is False
    assert evidence["model_updated"] is False
    assert evidence["control_write_performed"] is False


def test_assistant_skips_history_match_without_usable_fault_code(monkeypatch, tmp_path):
    monkeypatch.setenv("SELF_BRAIN_MAINTENANCE_DB", str(tmp_path / "empty.sqlite3"))
    monkeypatch.setattr(
        industrial_assistant,
        "_latest_machine_reading",
        lambda machine_id: {
            "timestamp": "2026-10-21T10:00:00Z",
            "machine_id": machine_id,
            "temperature_c": 65.0,
            "pressure_bar": 55.0,
            "vibration_mm_s": 3.0,
            "cycle_count": 1200,
            "downtime_minutes": 0,
            "fault_code": "NONE",
        },
    )

    result = industrial_assistant.ask_industrial_assistant({
        "machine_id": "M-001",
        "question": "What is the condition?",
    })

    evidence = result["evidence"]["verified_maintenance_context"]
    assert evidence["evidence_count"] == 0
    assert "No usable fault code" in evidence["interpretation"]
