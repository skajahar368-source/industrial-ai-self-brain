from ml.time_series_intelligence import analyze_trends


def reading(temp, vibration, pressure=55.0, downtime=0.0, step=0):
    return {
        "timestamp": f"2026-09-27T10:{step:02d}:00Z",
        "temperature_c": temp,
        "pressure_bar": pressure,
        "vibration_mm_s": vibration,
        "downtime_minutes": downtime,
    }


def test_empty_series_needs_more_data():
    result = analyze_trends([])
    assert result["status"] == "insufficient_data"


def test_rising_temperature_and_vibration_are_detected():
    result = analyze_trends([
        reading(61, 2.8, step=0),
        reading(64, 3.4, step=1),
        reading(68, 4.2, step=2),
        reading(73, 5.0, step=3),
    ])
    assert result["trend"] == "deteriorating"
    assert "temperature_rising" in result["signals"]
    assert "vibration_rising" in result["signals"]


def test_stable_series_has_no_deterioration_signal():
    result = analyze_trends([
        reading(61, 2.8, step=0),
        reading(61.1, 2.82, step=1),
        reading(61.0, 2.79, step=2),
    ])
    assert result["trend"] == "stable"
    assert result["signals"] == []


def test_pressure_and_downtime_trends_are_detected():
    result = analyze_trends([
        reading(70, 5, pressure=55, downtime=1, step=0),
        reading(71, 5.1, pressure=57, downtime=2, step=1),
        reading(72, 5.2, pressure=59, downtime=3, step=2),
    ])
    assert "pressure_rising" in result["signals"]
    assert "downtime_increasing" in result["signals"]
