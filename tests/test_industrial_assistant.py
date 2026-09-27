from ml.industrial_assistant import ask_industrial_assistant


def test_assistant_answers_machine_health_question():
    result = ask_industrial_assistant(
        {
            "machine_id": "M-001",
            "question": "What is the health and maintenance risk?",
        }
    )
    assert result["status"] == "ok"
    assert result["intent"] == "health"
    assert "M-001" in result["answer"]
    assert result["evidence"]["maintenance_risk"]["risk_level"] in {"low", "medium", "high"}


def test_assistant_uses_history_for_failure_question():
    result = ask_industrial_assistant(
        {
            "machine_id": "M-001",
            "question": "What previous failures should I check?",
        }
    )
    assert result["intent"] == "history"
    assert result["evidence"]["maintenance_event_count"] >= 1
    assert "Recorded maintenance events" in result["answer"]


def test_assistant_requires_machine_id():
    result = ask_industrial_assistant({"question": "What is happening?"})
    assert result["status"] == "blocked"


def test_assistant_requires_question():
    result = ask_industrial_assistant({"machine_id": "M-001"})
    assert result["status"] == "blocked"


def test_assistant_handles_unknown_machine():
    result = ask_industrial_assistant(
        {"machine_id": "M-999", "question": "What is the machine status?"}
    )
    assert result["status"] == "not_found"
