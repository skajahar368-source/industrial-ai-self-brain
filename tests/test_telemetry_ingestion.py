from ml.telemetry_ingestion import ingest_batch, ingest_reading, recent_telemetry


def payload(sequence_id="SEQ-001", machine_id="M-001"):
    return {
        "timestamp": "2026-09-27T10:00:00+05:30",
        "machine_id": machine_id,
        "temperature_c": 72.5,
        "pressure_bar": 55,
        "vibration_mm_s": 4.2,
        "cycle_count": 2000,
        "downtime_minutes": 2,
        "fault_code": "NONE",
        "source": "test-plc",
        "sequence_id": sequence_id,
    }


def test_ingest_accepts_normalized_reading():
    result = ingest_reading(payload("TEST-ACCEPT-001"))
    assert result["status"] == "accepted"
    assert result["reading"]["machine_id"] == "M-001"


def test_ingest_deduplicates_sequence_id():
    first = ingest_reading(payload("TEST-DUP-001"))
    second = ingest_reading(payload("TEST-DUP-001"))
    assert first["status"] == "accepted"
    assert second["status"] == "duplicate"


def test_batch_reports_rejected_records():
    result = ingest_batch(
        [
            payload("TEST-BATCH-001"),
            {**payload("TEST-BATCH-002"), "temperature_c": -1},
        ]
    )
    assert result["accepted"] == 1
    assert result["rejected"] == 1


def test_recent_telemetry_can_filter_machine():
    ingest_reading(payload("TEST-RECENT-001", "M-009"))
    result = recent_telemetry("M-009", limit=5)
    assert result
    assert result[0]["machine_id"] == "M-009"


def test_ingest_requires_machine_id():
    bad = payload("TEST-MISSING-MACHINE")
    bad["machine_id"] = ""
    result = None
    try:
        ingest_reading(bad)
    except ValueError as exc:
        result = str(exc)
    assert result == "machine_id cannot be empty"
