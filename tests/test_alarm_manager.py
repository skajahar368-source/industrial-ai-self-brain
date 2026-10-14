from ml.alarm_manager import AlarmManager
from ml.plc_gateway import PLCGateway
from ml.virtual_plc import VirtualPLC


def test_alarm_is_created_once_and_repeated_scans_update_last_seen():
    manager = AlarmManager()
    snapshot = {
        "machine_id": "M-ALARM",
        "state": "FAULT",
        "fault_code": "HIGH_TEMP",
        "alarm_active": True,
    }

    first = manager.observe(snapshot)
    second = manager.observe(snapshot)
    result = manager.snapshot("M-ALARM")

    assert first["alarm_id"] == second["alarm_id"]
    assert result["count"] == 1
    assert result["active_count"] == 1
    assert result["alarms"][0]["severity"] == "critical"
    assert result["control_write_performed"] is False


def test_alarm_is_cleared_when_plc_reports_normal_state():
    manager = AlarmManager()
    manager.observe({
        "machine_id": "M-CLEAR",
        "state": "FAULT",
        "fault_code": "HIGH_VIBRATION",
        "alarm_active": True,
    })

    manager.observe({
        "machine_id": "M-CLEAR",
        "state": "RUNNING",
        "fault_code": "NONE",
        "alarm_active": False,
    })
    result = manager.snapshot("M-CLEAR")

    assert result["count"] == 1
    assert result["active_count"] == 0
    assert result["alarms"][0]["active"] is False
    assert result["alarms"][0]["cleared_at"] is not None


def test_acknowledgement_changes_log_only_and_does_not_clear_alarm():
    manager = AlarmManager()
    alarm = manager.observe({
        "machine_id": "M-ACK",
        "state": "FAULT",
        "fault_code": "HIGH_TEMP",
        "alarm_active": True,
    })

    acknowledged = manager.acknowledge(alarm["alarm_id"], "maintenance-tech")

    assert acknowledged["acknowledged"] is True
    assert acknowledged["acknowledged_by"] == "maintenance-tech"
    assert acknowledged["active"] is True
    assert acknowledged["control_write_performed"] is False


def test_alarm_manager_rejects_unknown_ids_and_empty_acknowledger():
    manager = AlarmManager()
    try:
        manager.acknowledge("AL-999999", "maintenance-tech")
    except ValueError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("Expected unknown alarm to be rejected")

    try:
        manager.acknowledge("AL-000001", "")
    except ValueError as exc:
        assert "acknowledged_by" in str(exc)
    else:
        raise AssertionError("Expected empty acknowledger to be rejected")


def test_gateway_returns_alarm_summary_without_control_writes():
    gateway = PLCGateway(VirtualPLC("M-GATE-ALARM", "combined"))

    result = gateway.scan()

    assert result["alarms"]["active_count"] == 1
    assert result["alarms"]["alarms"][0]["machine_id"] == "M-GATE-ALARM"
    assert result["control_write_performed"] is False
