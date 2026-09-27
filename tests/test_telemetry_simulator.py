from ml.telemetry_simulator import generate_batch, generate_reading


def test_simulator_generates_normal_reading():
    reading = generate_reading("M-001", step=0, scenario="normal")
    assert reading["source"] == "self-brain-simulator"
    assert reading["fault_code"] == "NONE"
    assert reading["temperature_c"] < 65


def test_simulator_warning_progresses_toward_failure():
    reading = generate_reading("M-001", step=15, scenario="warning")
    assert reading["temperature_c"] > 75
    assert reading["vibration_mm_s"] > 8


def test_simulator_failure_is_high_risk():
    reading = generate_reading("M-001", step=10, scenario="failure")
    assert reading["temperature_c"] >= 80
    assert reading["pressure_bar"] >= 100
    assert reading["vibration_mm_s"] >= 8


def test_simulator_batch_has_unique_sequences():
    readings = generate_batch("M-002", start_step=5, count=4, scenario="normal")
    assert len(readings) == 4
    assert len({item["sequence_id"] for item in readings}) == 4


def test_simulator_rejects_unknown_scenario():
    try:
        generate_reading(scenario="unknown")
    except ValueError as exc:
        assert "scenario must be one of" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
