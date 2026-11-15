from ml.machine_maintenance_context import build_machine_maintenance_context


def test_builds_machine_scoped_context_and_keeps_sources_separate():
    result = build_machine_maintenance_context(
        "M-1",
        [
            {"machine_id": "M-1", "timestamp": "2026-11-15T10:00:00Z", "temperature_c": 80},
            {"machine_id": "M-2", "timestamp": "2026-11-15T11:00:00Z", "temperature_c": 99},
        ],
        {"alarms": [
            {"machine_id": "M-1", "active": True, "fault_code": "HIGH_VIBRATION"},
            {"machine_id": "M-2", "active": True, "fault_code": "OVER_TEMP"},
        ]},
        {"status": "ok", "events": [
            {"machine_id": "M-1", "event_type": "verified_maintenance",
             "evidence_label": "human_verified_maintenance_record"},
            {"machine_id": "M-2", "event_type": "investigation_report"},
        ]},
        {"status": "ok", "summaries": [
            {"machine_id": "M-1", "verified_cases": 2},
            {"machine_id": "M-2", "verified_cases": 9},
        ]},
        {"status": "ok", "events": [
            {"machine_id": "M-1", "event_type": "install"},
        ], "active_components": [
            {"machine_id": "M-1", "component_id": "C-1"},
        ]},
        {"status": "ok", "completed_lifecycles": [
            {"machine_id": "M-1", "component_id": "C-0"},
            {"machine_id": "M-2", "component_id": "C-2"},
        ], "part_summaries": []},
    )
    assert result["status"] == "ok"
    assert result["current_snapshot"]["latest_telemetry"]["temperature_c"] == 80
    assert len(result["current_snapshot"]["active_alarms"]) == 1
    assert result["historical_evidence"]["maintenance_effectiveness"]["verified_case_count"] == 2
    assert result["historical_evidence"]["component_lifecycle"]["active_component_count"] == 1
    assert result["historical_evidence"]["component_service_life"]["completed_lifecycle_count"] == 1
    assert result["evidence_coverage"]["verified_maintenance_available"] is True
    assert result["automatic_diagnosis_performed"] is False
    assert result["causal_relationship_inferred"] is False
    assert result["plc_write_performed"] is False


def test_empty_sources_are_reported_as_missing_not_as_normal():
    result = build_machine_maintenance_context(
        "M-EMPTY", [], {}, {}, {}, {}, {}
    )
    assert result["status"] == "ok"
    assert result["current_snapshot"]["latest_telemetry"] is None
    assert result["evidence_coverage"]["telemetry_available"] is False
    assert result["evidence_coverage"]["missing_sources_are_not_evidence_of_normal_condition"] is True


def test_rejects_empty_machine_id_and_invalid_telemetry_shape():
    assert build_machine_maintenance_context(" ", [], {}, {}, {}, {}, {})["status"] == "rejected"
    assert build_machine_maintenance_context("M-1", None, {}, {}, {}, {}, {})["status"] == "rejected"


def test_includes_telemetry_quality_without_treating_it_as_a_machine_fault():
    quality = {
        "status": "ok",
        "quality": "degraded",
        "issues": [{"type": "stale_reading", "age_seconds": 90}],
        "issue_count": 1,
        "checked_readings": 1,
    }
    result = build_machine_maintenance_context(
        "M-QUALITY", [], {}, {}, {}, {}, {}, telemetry_quality=quality
    )
    assert result["telemetry_data_quality"]["quality"] == "degraded"
    assert result["telemetry_data_quality"]["issue_count"] == 1
    assert result["evidence_coverage"]["telemetry_quality_degraded"] is True
    assert "not machine faults" in result["telemetry_data_quality"]["interpretation"]


def test_telemetry_quality_defaults_to_unknown_when_not_supplied():
    result = build_machine_maintenance_context(
        "M-UNKNOWN", [], {}, {}, {}, {}, {}
    )
    assert result["telemetry_data_quality"]["quality"] == "unknown"
    assert result["evidence_coverage"]["telemetry_quality_degraded"] is False
