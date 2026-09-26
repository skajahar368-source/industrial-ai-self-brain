from ml.historical_diagnosis import diagnose_against_history


def test_current_overheating_matches_previous_failure():
    result = diagnose_against_history(
        {
            "machine_id": "M-001",
            "temperature_c": 88,
            "pressure_bar": 60,
            "vibration_mm_s": 2,
            "downtime_minutes": 5,
            "fault_code": "F-101",
        }
    )
    assert result["historical_match"] is True
    assert result["recommendation"]["part"] == "Cooling Fan CF-24"
    assert result["recommendation"]["decision"] == "inspect_then_consider_replacement"


def test_new_cause_does_not_directly_recommend_a_part():
    result = diagnose_against_history(
        {
            "machine_id": "M-001",
            "temperature_c": 45,
            "pressure_bar": 60,
            "vibration_mm_s": 9,
            "downtime_minutes": 5,
            "fault_code": "F-999",
        }
    )
    assert result["recommendation"]["part"] is None
