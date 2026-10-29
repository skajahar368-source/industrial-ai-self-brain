import math

import pytest

from ml.telemetry_simulator import generate_reading
from ml.virtual_plc import build_virtual_plc_snapshot


def test_virtual_plc_normal_reading_maps_tags_and_registers():
    reading = generate_reading("M-PLC-01", step=3, scenario="normal")
    snapshot = build_virtual_plc_snapshot(reading)

    assert snapshot["status"] == "ok"
    assert snapshot["machine_state"] == "RUNNING"
    assert snapshot["alarm_state"] == "CLEAR"
    assert snapshot["tags"]["TemperatureC"] == reading["temperature_c"]
    assert snapshot["registers"]["DB1.DBD0"] == reading["temperature_c"]
    assert snapshot["read_only"] is True
    assert snapshot["real_plc_connected"] is False
    assert snapshot["write_commands_supported"] is False


def test_virtual_plc_warning_sets_degraded_state():
    snapshot = build_virtual_plc_snapshot(
        generate_reading("M-PLC-02", step=15, scenario="warning")
    )
    assert snapshot["machine_state"] == "DEGRADED"
    assert snapshot["alarm_state"] == "WARNING"


def test_virtual_plc_failure_sets_fault_alarm():
    snapshot = build_virtual_plc_snapshot(
        generate_reading("M-PLC-03", step=10, scenario="failure")
    )
    assert snapshot["machine_state"] == "FAULT"
    assert snapshot["alarm_state"] == "ACTIVE"


@pytest.mark.parametrize("bad_value", [None, "not-a-number", float("nan"), float("inf"), True])
def test_virtual_plc_rejects_invalid_sensor_values(bad_value):
    reading = generate_reading()
    reading["temperature_c"] = bad_value
    with pytest.raises(ValueError, match="temperature_c"):
        build_virtual_plc_snapshot(reading)


def test_virtual_plc_rejects_missing_fields():
    with pytest.raises(ValueError, match="missing required fields"):
        build_virtual_plc_snapshot({"machine_id": "M-01"})


def test_virtual_plc_rejects_negative_sensor_values():
    reading = generate_reading()
    reading["vibration_mm_s"] = -1
    with pytest.raises(ValueError, match="cannot be negative"):
        build_virtual_plc_snapshot(reading)
