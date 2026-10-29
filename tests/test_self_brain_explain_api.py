import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from ml.synthetic_self_brain import simulate_machine

client = TestClient(app)


class FakeBrain:
    def diagnose(self, readings, machine_id=None):
        assert len(readings) >= 12
        return {
            "status": "ok",
            "machine_id": machine_id,
            "predicted_fault": "vibration",
            "confidence": 0.8,
            "anomaly": True,
            "estimated_rul_steps": 12.5,
            "human_decision_required": True,
            "provenance": "synthetic_training_data",
        }


def _readings():
    return simulate_machine(
        "M-EXPLAIN-API",
        np.random.default_rng(41),
        n_steps=24,
        fault="vibration",
    ).to_dict("records")


def test_combined_self_brain_diagnosis_is_read_only(monkeypatch):
    from app.api import self_brain_explain_routes

    monkeypatch.setattr(self_brain_explain_routes, "_EXPLAINER_BRAIN", FakeBrain())
    monkeypatch.delenv("SELF_BRAIN_LLM_API_KEY", raising=False)
    response = client.post(
        "/api/self-brain/diagnose/explain",
        json={
            "machine_id": "M-EXPLAIN-API",
            "readings": _readings(),
            "reference_time": "2026-01-01T00:01:55+00:00",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["rule_based_diagnosis"]["analysis_type"] == "deterministic_rules"
    assert body["ml_diagnosis"]["predicted_fault"] == "vibration"
    assert body["data_provenance"] == "provided_telemetry; model trained on synthetic data"
    assert body["explanation"]["status"] == "not_configured"
    assert body["read_only"] is True
    assert body["real_plc_connected"] is False
    assert body["write_commands_supported"] is False
    assert body["human_decision_required"] is True


def test_combined_self_brain_diagnosis_rejects_empty_readings():
    response = client.post("/api/self-brain/diagnose/explain", json={"readings": []})
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_combined_self_brain_diagnosis_rejects_missing_sensor(monkeypatch):
    readings = _readings()
    readings[-1].pop("temperature_c")
    response = client.post(
        "/api/self-brain/diagnose/explain",
        json={
            "readings": readings,
            "reference_time": "2026-01-01T00:01:55+00:00",
        },
    )
    assert response.status_code == 200
    assert response.json()["reason"] == "telemetry_quality"
    assert response.json()["read_only"] is True
