from ml.failure_pattern_learning import (
    build_failure_patterns,
    learn_failure_pattern,
    record_learning_outcome,
    summarize_learning_outcomes,
)


def test_repeated_historical_pattern_is_learned():
    result = learn_failure_pattern(
        {
            "machine_id": "M-001",
            "fault_code": "F-101",
            "causes": ["Overheating"],
        }
    )
    assert result["status"] == "pattern_match"
    assert result["matched_pattern"]["part_replaced"] == "cooling fan cf-24"
    assert "same_cause" in result["evidence"]
    assert "same_fault_code" in result["evidence"]


def test_unknown_pattern_does_not_recommend_replacement():
    result = learn_failure_pattern(
        {
            "machine_id": "M-001",
            "fault_code": "F-999",
            "causes": ["Unknown cause"],
        }
    )
    assert result["status"] == "no_strong_pattern"
    assert "do not directly replace" in result["recommendation"]


def test_patterns_can_be_scoped_to_machine():
    patterns = build_failure_patterns("M-002")
    assert patterns
    assert all(pattern["machine_id"] == "M-002" for pattern in patterns)


def test_learning_outcomes_have_success_rate():
    result = summarize_learning_outcomes()
    assert result["count"] == 3
    assert result["successful_repairs"] == 3
    assert result["success_rate"] == 1.0


def test_learning_outcome_requires_verification():
    result = record_learning_outcome(
        {
            "event_timestamp": "2026-09-26T10:00:00",
            "machine_id": "M-001",
            "fault_code": "F-101",
            "cause": "Overheating",
            "part_replaced": "Cooling Fan CF-24",
            "repair_successful": True,
            "verification_result": "",
        }
    )
    assert result["status"] == "blocked"
