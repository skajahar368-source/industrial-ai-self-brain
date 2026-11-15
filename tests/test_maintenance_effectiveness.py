from ml.maintenance_effectiveness import summarize_maintenance_effectiveness


def case(**overrides):
    item = {
        "outcome_id": "case-1",
        "event_timestamp": "2026-10-01T10:00:00Z",
        "machine_id": "M-01",
        "fault_code": "HIGH_VIBRATION",
        "cause": "bearing wear",
        "repair_action": "replace bearing",
        "repair_successful": True,
        "verified": True,
        "before_evidence": "vibration high",
        "after_evidence": "vibration normal",
        "verified_by": "engineer",
        "verification_method": "measurement",
        "verification_result": "within baseline",
    }
    item.update(overrides)
    return item


def test_effectiveness_summary_counts_verified_cases_and_repeat_interval():
    result = summarize_maintenance_effectiveness([
        case(),
        case(
            outcome_id="case-2",
            event_timestamp="2026-10-03T10:00:00Z",
            repair_successful=False,
            repair_action="inspect mounting",
        ),
        case(machine_id="M-02"),
        case(verified=False, outcome_id="unverified"),
    ], machine_id="M-01")

    assert result["status"] == "ok"
    assert result["verified_cases"] == 2
    assert result["successful_repairs"] == 1
    assert result["recorded_success_rate"] == 0.5
    summary = result["summaries"][0]
    assert summary["recurrence_observed"] is True
    assert summary["repeat_intervals_days"] == [2.0]
    assert summary["before_after_evidence_cases"] == 2
    assert result["unverified_records_included"] is False
    assert result["causal_effectiveness_claimed"] is False
    assert result["plc_write_performed"] is False


def test_effectiveness_filters_fault_code_and_skips_bad_timestamps():
    result = summarize_maintenance_effectiveness([
        case(),
        case(fault_code="OVERHEAT", outcome_id="case-2"),
        case(event_timestamp="not-a-date", outcome_id="bad"),
    ], fault_code="high_vibration")

    assert result["groups"] == 1
    assert result["summaries"][0]["fault_code"] == "HIGH_VIBRATION"
    assert result["verified_cases"] == 1


def test_effectiveness_empty_history_and_invalid_filters():
    empty = summarize_maintenance_effectiveness([])
    assert empty["status"] == "ok"
    assert empty["verified_cases"] == 0
    assert empty["recorded_success_rate"] is None
    assert summarize_maintenance_effectiveness([], machine_id=" ")["status"] == "rejected"
    assert summarize_maintenance_effectiveness([], fault_code=" ")["status"] == "rejected"


def test_naive_timestamps_are_treated_as_utc():
    result = summarize_maintenance_effectiveness([
        case(event_timestamp="2026-10-01T10:00:00")
    ])
    assert result["summaries"][0]["cases"][0]["event_timestamp"] == "2026-10-01T10:00:00+00:00"
