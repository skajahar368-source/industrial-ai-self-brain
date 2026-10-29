from math import nan

import pytest

from ml.telemetry_quality import assess_telemetry_quality


def reading(timestamp, temperature=60.0, pressure=55.0, vibration=3.0, machine_id="M-QUALITY"):
    return {
        "timestamp": timestamp,
        "machine_id": machine_id,
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
    assert any(issue["type"] == "stuck_sensor" and issue["sensor"] == "temperature_c" for issue in result["issues"])


def test_quality_flags_sudden_spike():
    result = assess_telemetry_quality(
        [
            reading("2026-09-27T10:00:00+00:00", temperature=60.0),
            reading("2026-09-27T10:00:05+00:00", temperature=85.0),
        ],
        reference_time="2026-09-27T10:00:05+00:00",
        stale_after_seconds=60,
    )
    assert any(issue["type"] == "sudden_spike" and issue["sensor"] == "temperature_c" for issue in result["issues"])


def test_quality_flags_missing_sensor():
    payload = reading("2026-09-27T10:00:00+00:00")
    del payload["vibration_mm_s"]
    result = assess_telemetry_quality([payload], reference_time="2026-09-27T10:00:00+00:00")
    assert any(issue["type"] == "missing_sensor" and issue["sensor"] == "vibration_mm_s" for issue in result["issues"])


def test_quality_is_good_for_clean_reading():
    result = assess_telemetry_quality(
        [reading("2026-09-27T10:00:00+00:00")],
        reference_time="2026-09-27T10:00:00+00:00",
    )
    assert result["quality"] == "good"
    assert result["issue_count"] == 0


def test_invalid_sensor_values_are_reported():
    result = assess_telemetry_quality(
        [reading("2026-09-27T10:00:00+00:00", temperature=nan)],
        reference_time="2026-09-27T10:00:00+00:00",
    )
    assert any(issue["type"] == "invalid_sensor_value" and issue["sensor"] == "temperature_c" for issue in result["issues"])


def test_future_timestamps_are_reported():
    result = assess_telemetry_quality(
        [reading("2026-09-27T10:02:00+00:00")],
        reference_time="2026-09-27T10:00:00+00:00",
    )
    assert any(issue["type"] == "future_timestamp" for issue in result["issues"])


def test_readings_are_sorted_using_parsed_timestamps():
    result = assess_telemetry_quality(
        [
            reading("2026-09-27T10:00:05+00:00", temperature=85.0),
            reading("2026-09-27T12:00:00+02:00", temperature=60.0),
        ],
        reference_time="2026-09-27T10:00:05+00:00",
    )
    assert result["checked_readings"] == 2
    assert any(issue["type"] == "sudden_spike" for issue in result["issues"])


def test_readings_from_different_machines_are_not_compared_for_spikes():
    result = assess_telemetry_quality(
        [
            reading("2026-09-27T10:00:00+00:00", temperature=60, machine_id="M-A"),
            reading("2026-09-27T10:00:05+00:00", temperature=95, machine_id="M-B"),
        ],
        reference_time="2026-09-27T10:00:05+00:00",
    )
    assert not any(issue["type"] == "sudden_spike" for issue in result["issues"])


@pytest.mark.parametrize("threshold", [0, -1, nan, float("inf"), "bad"])
def test_invalid_spike_threshold_is_rejected(threshold):
    with pytest.raises(ValueError, match="spike threshold"):
        assess_telemetry_quality(
            [reading("2026-09-27T10:00:00+00:00")],
            reference_time="2026-09-27T10:00:00+00:00",
            spike_thresholds={"temperature_c": threshold},
        )


def test_non_object_reading_is_rejected():
    with pytest.raises(ValueError, match="each reading must be an object"):
        assess_telemetry_quality([None])
