"""Industrial Validation Lab: deterministic, simulation-only fault scenarios.

These tests validate software behavior, not the safety or accuracy of a real
factory installation. They intentionally keep the PLC interface read-only.
"""
from __future__ import annotations

import pytest

from ml.alarm_manager import AlarmManager
from ml.plc_gateway import PLCGateway
from ml.virtual_plc import VirtualPLC


@pytest.mark.parametrize("scenario", ["normal"])
def test_normal_baseline_has_no_active_alarm(scenario: str) -> None:
    gateway = PLCGateway(VirtualPLC("M-LAB-NORMAL", scenario))

    result = gateway.scan()

    assert result["plc"]["scenario"] == scenario
    assert result["plc"]["fault_code"] == "NONE"
    assert result["plc"]["alarm_active"] is False
    assert result["alarms"]["active_count"] == 0
    assert result["control_write_performed"] is False


@pytest.mark.parametrize("scenario", ["thermal", "pressure", "vibration", "combined", "failure"])
def test_fault_scenarios_surface_alarm_evidence(scenario: str) -> None:
    gateway = PLCGateway(VirtualPLC(f"M-LAB-{scenario.upper()}", scenario))

    result = gateway.scan()

    assert result["plc"]["fault_code"] != "NONE"
    assert result["plc"]["alarm_active"] is True
    assert result["alarms"]["active_count"] == 1
    alarm = result["alarms"]["alarms"][0]
    assert alarm["machine_id"] == f"M-LAB-{scenario.upper()}"
    assert alarm["fault_code"] == result["plc"]["fault_code"]
    assert alarm["active"] is True
    assert result["control_write_performed"] is False


def test_repeated_fault_does_not_duplicate_active_alarm() -> None:
    gateway = PLCGateway(VirtualPLC("M-LAB-REPEAT", "combined"))

    first = gateway.scan()
    first_id = first["alarms"]["alarms"][0]["alarm_id"]
    for _ in range(20):
        result = gateway.scan()

    assert result["alarms"]["active_count"] == 1
    assert result["alarms"]["count"] == 1
    assert result["alarms"]["alarms"][0]["alarm_id"] == first_id
    assert result["control_write_performed"] is False


def test_normal_reading_closes_prior_alarm_without_plc_write() -> None:
    plc = VirtualPLC("M-LAB-RECOVERY", "combined")
    gateway = PLCGateway(plc)
    raised = gateway.scan()
    alarm_id = raised["alarms"]["alarms"][0]["alarm_id"]

    gateway.configure(scenario="normal")
    recovered = gateway.scan()
    history = gateway.alarm_manager.snapshot("M-LAB-RECOVERY")

    assert recovered["plc"]["fault_code"] == "NONE"
    assert history["active_count"] == 0
    assert history["count"] == 1
    assert history["alarms"][0]["alarm_id"] == alarm_id
    assert history["alarms"][0]["cleared_at"] is not None
    assert recovered["control_write_performed"] is False


def test_long_run_keeps_alarm_history_bounded() -> None:
    manager = AlarmManager(max_history=25)
    for i in range(100):
        manager.observe({
            "machine_id": f"M-LAB-STRESS-{i}",
            "state": "FAULT",
            "fault_code": "HIGH_TEMP",
            "alarm_active": True,
        })

    result = manager.snapshot()
    assert result["count"] == 25
    assert result["active_count"] == 25
    assert result["read_only_to_plc"] is True


def test_invalid_alarm_inputs_are_rejected() -> None:
    manager = AlarmManager()
    with pytest.raises(ValueError, match="machine_id"):
        manager.observe({"machine_id": "", "fault_code": "HIGH_TEMP", "alarm_active": True})
    with pytest.raises(ValueError, match="positive"):
        AlarmManager(max_history=0)
