from ml.component_lifecycle import component_lifecycle_history, record_component_event


def install(**overrides):
    data = {
        "event_id": "install-1", "event_type": "install", "machine_id": "M-01",
        "component_id": "MOTOR-001", "part_number": "MTR-22", "part_name": "Drive motor",
        "event_timestamp": "2026-01-01T08:00:00Z", "runtime_hours": 100,
        "production_cycles": 500,
    }
    data.update(overrides)
    return data


def test_install_inspect_remove_and_history(tmp_path):
    db = tmp_path / "lifecycle.sqlite3"
    assert record_component_event(install(), db)["status"] == "recorded"
    inspected = record_component_event({
        "event_id": "inspect-1", "event_type": "inspection", "machine_id": "M-01",
        "component_id": "MOTOR-001", "event_timestamp": "2026-01-10T08:00:00Z",
        "runtime_hours": 150, "production_cycles": 900, "condition": "normal",
        "evidence": "visual inspection",
    }, db)
    assert inspected["status"] == "recorded"
    removed = record_component_event({
        "event_id": "remove-1", "event_type": "remove", "machine_id": "M-01",
        "component_id": "MOTOR-001", "event_timestamp": "2026-02-01T08:00:00Z",
        "runtime_hours": 300, "production_cycles": 2000,
        "removal_reason": "bearing noise", "maintenance_action": "replaced motor",
    }, db)
    assert removed["status"] == "recorded"
    history = component_lifecycle_history("M-01", db_path=db)
    assert history["event_count"] == 3
    assert history["active_component_count"] == 0
    assert history["events"][0]["event_type"] == "remove"
    assert history["plc_write_performed"] is False


def test_rejects_duplicate_active_install_and_remove_without_install(tmp_path):
    db = tmp_path / "lifecycle.sqlite3"
    assert record_component_event(install(), db)["status"] == "recorded"
    duplicate = install(event_id="install-2", event_timestamp="2026-01-02T08:00:00Z")
    assert record_component_event(duplicate, db)["status"] == "rejected"
    missing = record_component_event({
        "event_type": "remove", "machine_id": "M-01", "component_id": "MISSING",
        "event_timestamp": "2026-01-03T08:00:00Z", "runtime_hours": 120,
        "production_cycles": 600, "removal_reason": "failed",
    }, db)
    assert missing["status"] == "rejected"


def test_rejects_invalid_meters_and_duplicate_event_ids(tmp_path):
    db = tmp_path / "lifecycle.sqlite3"
    assert record_component_event(install(), db)["status"] == "recorded"
    bad = record_component_event({
        "event_type": "inspection", "machine_id": "M-01", "component_id": "MOTOR-001",
        "event_timestamp": "2026-01-02T08:00:00Z", "runtime_hours": -1,
        "production_cycles": 600,
    }, db)
    assert bad["status"] == "rejected"
    duplicate = record_component_event(install(), db)
    assert duplicate["status"] == "rejected"


def test_active_installation_remains_in_ledger(tmp_path):
    db = tmp_path / "lifecycle.sqlite3"
    record_component_event(install(), db)
    history = component_lifecycle_history("M-01", db_path=db)
    assert history["active_component_count"] == 1
    assert history["active_components"][0]["part_number"] == "MTR-22"
