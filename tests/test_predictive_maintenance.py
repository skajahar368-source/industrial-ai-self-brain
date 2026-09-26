from ml.predictive_maintenance import maintenance_risk


def test_high_risk_reading():
    result = maintenance_risk(
        {
            "temperature_c": 85,
            "pressure_bar": 102,
            "vibration_mm_s": 9,
            "downtime_minutes": 35,
            "fault_code": "HIGH_TEMP_PRESSURE",
        }
    )
    assert result["risk_level"] == "high"
    assert result["maintenance_risk_score"] >= 70


def test_low_risk_reading():
    result = maintenance_risk(
        {
            "temperature_c": 55,
            "pressure_bar": 55,
            "vibration_mm_s": 2,
            "downtime_minutes": 0,
            "fault_code": "NONE",
        }
    )
    assert result["risk_level"] == "low"
