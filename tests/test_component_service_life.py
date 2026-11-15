from ml.component_service_life import summarize_component_service_life


def sample_events():
    return [
        {
            "event_id": "i1", "event_type": "install", "machine_id": "M-1",
            "component_id": "C-1", "part_number": "BRG-6204", "part_name": "Bearing",
            "event_timestamp": "2026-01-01T00:00:00Z", "runtime_hours": 100,
            "production_cycles": 1000,
        },
        {
            "event_id": "r1", "event_type": "remove", "machine_id": "M-1",
            "component_id": "C-1", "event_timestamp": "2026-02-01T00:00:00Z",
            "runtime_hours": 300, "production_cycles": 5000,
            "removal_reason": "scheduled replacement",
        },
        {
            "event_id": "i2", "event_type": "install", "machine_id": "M-2",
            "component_id": "C-2", "part_number": "BRG-6204", "part_name": "Bearing",
            "event_timestamp": "2026-01-01T00:00:00Z", "runtime_hours": 50,
            "production_cycles": 500,
        },
        {
            "event_id": "r2", "event_type": "remove", "machine_id": "M-2",
            "component_id": "C-2", "event_timestamp": "2026-01-16T00:00:00Z",
            "runtime_hours": 150, "production_cycles": 2500,
            "removal_reason": "inspection finding",
        },
        {
            "event_id": "i3", "event_type": "install", "machine_id": "M-1",
            "component_id": "C-3", "part_number": "MOTOR-22", "part_name": "Motor",
            "event_timestamp": "2026-02-10T00:00:00Z", "runtime_hours": 310,
            "production_cycles": 5100,
        },
    ]


def test_calculates_recorded_usage_between_install_and_removal():
    result = summarize_component_service_life(sample_events(), machine_id="M-1")
    assert result["status"] == "ok"
    assert result["completed_lifecycle_count"] == 1
    case = result["completed_lifecycles"][0]
    assert case["runtime_hours_observed"] == 200
    assert case["production_cycles_observed"] == 4000
    assert case["calendar_days_observed"] == 31
    assert result["active_installation_count"] == 1


def test_aggregates_only_completed_records_by_part_number():
    result = summarize_component_service_life(sample_events())
    bearing = next(item for item in result["part_summaries"] if item["part_number"] == "BRG-6204")
    assert bearing["completed_lifecycle_count"] == 2
    assert bearing["average_runtime_hours_observed"] == 150
    assert bearing["average_production_cycles_observed"] == 3000
    assert result["failure_prediction_performed"] is False


def test_filters_by_part_number():
    result = summarize_component_service_life(sample_events(), part_number="motor-22")
    assert result["completed_lifecycle_count"] == 0
    assert result["part_summaries"] == []


def test_ignores_orphan_removal_and_invalid_timestamp():
    events = [
        {"event_type": "remove", "machine_id": "M-1", "component_id": "C-1"},
        {"event_type": "install", "machine_id": "M-1", "component_id": "C-2",
         "event_timestamp": "bad", "runtime_hours": 1, "production_cycles": 1},
    ]
    result = summarize_component_service_life(events)
    assert result["completed_lifecycle_count"] == 0
