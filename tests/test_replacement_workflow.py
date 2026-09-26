from ml.replacement_workflow import validate_early_replacement


def base_payload():
    return {
        "reason_code": "misalignment",
        "evidence_type": "measurement",
        "corrective_action": "Corrected alignment and checked coupling.",
        "verification_result": "Machine test run completed without abnormal vibration.",
        "replacement_approved": True,
    }


def test_valid_early_replacement_can_be_recorded():
    result = validate_early_replacement(base_payload())
    assert result["status"] == "approved_for_recording"


def test_early_replacement_requires_reason():
    payload = base_payload()
    payload.pop("reason_code")
    result = validate_early_replacement(payload)
    assert result["status"] == "blocked"


def test_early_replacement_requires_verification():
    payload = base_payload()
    payload["verification_result"] = ""
    result = validate_early_replacement(payload)
    assert result["status"] == "blocked"


def test_unknown_reason_requires_investigation_but_is_valid():
    payload = base_payload()
    payload["reason_code"] = "unknown"
    result = validate_early_replacement(payload)
    assert result["status"] == "approved_for_recording"
