from ml.production_monitor import summarize_production


def test_production_metrics_are_deterministic():
    result = summarize_production(
        machine_id="M-PROD",
        cycle_count=100,
        downtime_minutes=10,
        runtime_minutes=40,
        reject_count=5,
        ideal_cycle_seconds=20,
    )
    assert result["total_count"] == 100
    assert result["good_count"] == 95
    assert result["availability_percent"] == 80.0
    assert result["quality_percent"] == 95.0
    assert result["performance_percent"] == 83.33
    assert result["oee_percent"] == 63.33


def test_rejects_invalid_counts():
    try:
        summarize_production(
            machine_id="M-PROD",
            cycle_count=10,
            downtime_minutes=0,
            runtime_minutes=10,
            reject_count=11,
        )
    except ValueError as exc:
        assert "reject_count" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_production_metrics_from_plc_snapshot():
    from ml.production_monitor import summarize_plc_snapshot

    result = summarize_plc_snapshot({
        "machine_id": "M-PLC",
        "scan_counter": 120,
        "cycle_count": 100,
        "downtime_minutes": 2,
    })
    assert result["machine_id"] == "M-PLC"
    assert result["total_count"] == 100
    assert result["downtime_minutes"] == 2.0
    assert result["runtime_minutes"] == 8.0
