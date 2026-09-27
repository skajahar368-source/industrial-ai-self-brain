from ml.degradation_timeline import build_degradation_timeline


def reading(temp, vibration, pressure=55.0, downtime=0.0, fault="NONE", step=0):
    return {
        "timestamp": f"2026-09-27T10:{step:02d}:00Z",
        "temperature_c": temp,
        "pressure_bar": pressure,
        "vibration_mm_s": vibration,
        "downtime_minutes": downtime,
        "fault_code": fault,
    }


def test_empty_timeline_needs_data():
    result = build_degradation_timeline([])
    assert result["status"] == "insufficient_data"


def test_timeline_detects_deterioration():
    result = build_degradation_timeline([
        reading(61, 2.8, step=0),
        reading(70, 5.5, step=1),
        reading(82, 8.2, pressure=101, downtime=20, fault="HIGH_TEMP_PRESSURE", step=2),
    ])
    assert result["status"] == "ok"
    assert result["sample_count"] == 3
    assert result["end_risk"] > result["start_risk"]
    assert result["direction"] in {"deteriorating", "rapid_deterioration"}
    assert len(result["timeline"]) == 3


def test_timeline_contains_health_and_risk_per_point():
    result = build_degradation_timeline([
        reading(61, 2.8, step=0),
        reading(62, 2.9, step=1),
    ])
    point = result["timeline"][-1]
    assert "health_status" in point
    assert "maintenance_risk" in point
