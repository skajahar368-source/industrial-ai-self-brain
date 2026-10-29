import json

from fastapi.testclient import TestClient

from app.main import app
from ml.virtual_plc_explainer import (
    build_explanation_prompt,
    explain_virtual_plc_diagnosis,
)

client = TestClient(app)


def test_prompt_includes_rule_findings_and_safety_constraints():
    snapshot = {
        "machine_id": "M-LLM-01",
        "machine_state": "DEGRADED",
        "alarm_state": "ACTIVE",
        "tags": {"temperature_c": 88},
    }
    diagnosis = {"analysis_type": "deterministic_rules", "severity": "high", "findings": []}
    messages = build_explanation_prompt(snapshot, diagnosis)

    assert "Do not invent measurements" in messages[0]["content"]
    supplied = json.loads(messages[1]["content"])
    assert supplied["machine_id"] == "M-LLM-01"
    assert supplied["rule_diagnosis"]["analysis_type"] == "deterministic_rules"


def test_explanation_is_disabled_without_api_key(monkeypatch):
    monkeypatch.delenv("SELF_BRAIN_LLM_API_KEY", raising=False)
    result = explain_virtual_plc_diagnosis({"machine_id": "M-01"}, {"findings": []})

    assert result["status"] == "not_configured"
    assert result["analysis_is_ai_generated"] is False
    assert result["explanation"] is None


def test_explanation_marks_provider_output_as_ai_generated(monkeypatch):
    from ml import virtual_plc_explainer

    monkeypatch.setattr(virtual_plc_explainer, "call_chat_completion", lambda messages: "Observations: high vibration.")
    result = explain_virtual_plc_diagnosis({"machine_id": "M-02"}, {"findings": []})

    assert result["status"] == "ok"
    assert result["analysis_is_ai_generated"] is True
    assert "high vibration" in result["model_explanation"]


def test_virtual_plc_explain_endpoint_is_read_only_and_safe_without_key(monkeypatch):
    monkeypatch.delenv("SELF_BRAIN_LLM_API_KEY", raising=False)
    response = client.get(
        "/api/virtual-plc/explain",
        params={"machine_id": "M-EXPLAIN-01", "step": 10, "scenario": "failure"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["read_only"] is True
    assert body["real_plc_connected"] is False
    assert body["write_commands_supported"] is False
    assert body["human_decision_required"] is True
    assert body["explanation"]["status"] == "not_configured"
    assert body["diagnosis"]["analysis_type"] == "deterministic_rules"


def test_virtual_plc_explain_endpoint_rejects_unknown_scenario():
    response = client.get("/api/virtual-plc/explain", params={"scenario": "unknown"})
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
