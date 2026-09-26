from ml.root_cause import analyze_root_causes


def test_detects_multiple_contributing_causes():
    result = analyze_root_causes(
        {
            "temperature_c": 88,
            "pressure_bar": 105,
            "vibration_mm_s": 9,
            "downtime_minutes": 45,
            "fault_code": "F-101",
        }
    )
    assert result["status"] == "causes_detected"
    assert result["cause_count"] >= 4
    assert result["priority"] == "high"


def test_normal_reading_has_no_significant_cause():
    result = analyze_root_causes(
        {
            "temperature_c": 45,
            "pressure_bar": 60,
            "vibration_mm_s": 2,
            "downtime_minutes": 5,
            "fault_code": "",
        }
    )
    assert result["cause_count"] == 0
    assert result["status"] == "no_significant_cause_detected"
