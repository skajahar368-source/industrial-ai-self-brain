"""SQLite persistence tests for the Self-Brain alarm registry."""
from __future__ import annotations

from ml.alarm_manager import AlarmManager


def fault_snapshot(machine_id: str = "M-PERSIST") -> dict:
    return {
        "machine_id": machine_id,
        "state": "FAULT",
        "fault_code": "HIGH_TEMP",
        "alarm_active": True,
    }


def normal_snapshot(machine_id: str = "M-PERSIST") -> dict:
    return {
        "machine_id": machine_id,
        "state": "RUNNING",
        "fault_code": "NONE",
        "alarm_active": False,
    }


def test_alarm_and_acknowledgement_survive_manager_restart(tmp_path):
    database = tmp_path / "alarms.sqlite3"
    first_manager = AlarmManager(db_path=database)
    created = first_manager.observe(fault_snapshot())
    acknowledged = first_manager.acknowledge(created["alarm_id"], "maintenance-tech")
    first_manager.close()

    restarted_manager = AlarmManager(db_path=database)
    result = restarted_manager.snapshot("M-PERSIST")
    saved = result["alarms"][0]

    assert result["count"] == 1
    assert result["active_count"] == 1
    assert saved["alarm_id"] == created["alarm_id"]
    assert saved["acknowledged"] is True
    assert saved["acknowledged_by"] == "maintenance-tech"
    assert saved["acknowledged_at"] == acknowledged["acknowledged_at"]
    assert result["control_write_performed"] is False
    restarted_manager.close()


def test_active_alarm_can_be_cleared_after_restart(tmp_path):
    database = tmp_path / "recovery.sqlite3"
    first_manager = AlarmManager(db_path=database)
    raised = first_manager.observe(fault_snapshot("M-RECOVERY-PERSIST"))
    first_manager.close()

    restarted_manager = AlarmManager(db_path=database)
    restarted_manager.observe(normal_snapshot("M-RECOVERY-PERSIST"))
    result = restarted_manager.snapshot("M-RECOVERY-PERSIST")

    assert result["count"] == 1
    assert result["active_count"] == 0
    assert result["alarms"][0]["alarm_id"] == raised["alarm_id"]
    assert result["alarms"][0]["active"] is False
    assert result["alarms"][0]["cleared_at"] is not None
    assert result["control_write_performed"] is False
    restarted_manager.close()


def test_persistent_manager_keeps_alarm_ids_unique_after_restart(tmp_path):
    database = tmp_path / "ids.sqlite3"
    first_manager = AlarmManager(db_path=database)
    first = first_manager.observe(fault_snapshot("M-ID-ONE"))
    first_manager.close()

    second_manager = AlarmManager(db_path=database)
    second = second_manager.observe(fault_snapshot("M-ID-TWO"))

    assert first["alarm_id"] != second["alarm_id"]
    assert second["alarm_id"] == "AL-000002"
    assert second_manager.snapshot()["count"] == 2
    second_manager.close()


def test_persistent_history_respects_configured_limit(tmp_path):
    database = tmp_path / "bounded.sqlite3"
    manager = AlarmManager(max_history=2, db_path=database)
    for index in range(3):
        manager.observe(fault_snapshot(f"M-LIMIT-{index}"))
    manager.close()

    restarted_manager = AlarmManager(max_history=2, db_path=database)
    result = restarted_manager.snapshot()

    assert result["count"] == 2
    assert {item["machine_id"] for item in result["alarms"]} == {"M-LIMIT-1", "M-LIMIT-2"}
    restarted_manager.close()
