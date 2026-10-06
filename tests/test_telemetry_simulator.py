from ml.telemetry_simulator import generate_batch, generate_reading


def test_normal_reading_has_no_fault():
    reading = generate_reading("M-T", 0, "normal")
    assert reading["fault_code"] == "NONE"


def test_fault_injection_changes_sensor_signatures():
    thermal = generate_reading("M-T", 25, "thermal")
    pressure = generate_reading("M-P", 25, "pressure")
    vibration = generate_reading("M-V", 25, "vibration")
    assert thermal["temperature_c"] > 65
    assert pressure["pressure_bar"] > 70
    assert vibration["vibration_mm_s"] > 8


def test_batch_is_deterministic_and_bounded():
    rows = generate_batch("M-B", 0, 24, "combined")
    assert len(rows) == 24
    assert rows[0]["sequence_id"] == "SIM-M-B-combined-0"
    assert rows[-1]["cycle_count"] > rows[0]["cycle_count"]
