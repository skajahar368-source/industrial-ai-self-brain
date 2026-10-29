from ml.telemetry_simulator import generate_reading
from ml.virtual_plc_diagnosis import diagnose_virtual_plc_reading


def test_rule_diagnosis_reports_normal_simulated_reading():
    result = diagnose_virtual_plc_reading(generate_reading("M-RULE-01", step=1, scenario="normal"))
    assert result["analysis_type"] == "deterministic_rules"
    assert result["severity"] == "normal"
    assert result["finding_count"] == 0
    assert result["human_decision_required"] is True
    assert result["automated_machine_action"] is False


def test_rule_diagnosis_explains_high_sensor_values():
    reading = generate_reading("M-RULE-02", step=20, scenario="failure")
    result = diagnose_virtual_plc_reading(reading)
    codes = {finding["code"] for finding in result["findings"]}
    assert result["severity"] == "high"
    assert "HIGH_TEMPERATURE_C" in codes
    assert "HIGH_PRESSURE_BAR" in codes
    assert "HIGH_VIBRATION_MM_S" in codes


def test_rule_diagnosis_rejects_missing_required_fields():
    try:
        diagnose_virtual_plc_reading({"machine_id": "M-BAD"})
    except ValueError as exc:
        assert "missing required fields" in str(exc)
    else:
        raise AssertionError("missing fields must be rejected")
