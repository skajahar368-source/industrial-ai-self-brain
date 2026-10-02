from ml.telemetry_quality import assess_telemetry_quality


def reading(timestamp, temperature=60.0, pressure=55.0, vibration=3.0):
    return {
        "timestamp": timestamp,
        "machine_id": "M-QUALITY",
        "temperature_c": temperature,
        "pressure_bar": pressure,
        "vibration_mm_s": vibration,
        "cycle_count": 1000,
        "downtime_minutes": 0,
        "fault_code": "NONE",
    }


def test_quality_flags_stale_reading():
    result = assess_telemetry_quality(
        [reading("2026-09-27T09:58:00+00:00")],
        reference_time="2026-09-27T10:00:00+00:00",
        stale_after_seconds=60,
    )
    assert result["quality"] == "degraded"
    assert any(issue["type"] == "stale_reading" for issue in result["issues"])


def test_quality_flags_stuck_sensor():
    result = assess_telemetry_quality(
        [
            reading("2026-09-27T10:00:00+00:00"),
            reading("2026-09-27T10:00:05+00:00"),
            reading("2026-09-27T10:00:10+00:00"),
        ],
        reference_time="2026-09-27T10:00:10+00:00",
        stale_after_seconds=60,
        stuck_window=3,
    )
    assert any(
        issue["type"] == "stuck_sensor" and issue["sensor"] == "temperature_c"
        for issue in result["issues"]
    )


def test_quality_flags_sudden_spike():
    result = assess_telemetry_quality(
        [
            reading("2026-09-27T10:00:00+00:00", temperature=60.0),
            reading("2026-09-27T10:00:05+00:00", temperature=85.0),
        ],
        reference_time="2026-09-27T10:00:05+00:00",
        stale_after_seconds=60,
    )
    assert any(
        issue["type"] == "sudden_spike" and issue["sensor"] == "temperature_c"
        for issue in result["issues"]
    )


def test_quality_flags_missing_sensor():
    payload = reading("2026-09-27T10:00:00+00:00")
    del payload["vibration_mm_s"]
    result = assess_telemetry_quality(
        [payload],
        reference_time="2026-09-27T10:00:00+00:00",
    )
    assert any(
        issue["type"] == "missing_sensor" and issue["sensor"] == "vibration_mm_s"
        for issue in result["issues"]
    )


def test_quality_is_good_for_clean_reading():
    result = assess_telemetry_quality(
        [reading("2026-09-27T10:00:00+00:00")],
        reference_time="2026-09-27T10:00:00+00:00",
    )
    assert result["quality"] == "good"
    assert result["issue_count"] == 0
