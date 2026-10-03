from app.api.routes import self_brain_diagnose, self_brain_status, self_brain_train
from ml.synthetic_self_brain import simulate_machine
import numpy as np


def test_self_brain_api_trains_and_reports_status():
    trained = self_brain_train()
    assert trained["status"] == "trained"
    assert self_brain_status()["trained"] is True


def test_self_brain_api_rejects_missing_sensor_before_model():
    readings = simulate_machine("M-API", np.random.default_rng(2), n_steps=20).to_dict("records")
    readings[-1].pop("temperature_c")
    result = self_brain_diagnose({"readings": readings, "reference_time": "2026-01-01T00:02:00+00:00"})
    assert result["status"] == "rejected"
    assert result["reason"] == "telemetry_quality"


def test_self_brain_api_returns_machine_diagnosis():
    readings = simulate_machine("M-API", np.random.default_rng(3), n_steps=24, fault="vibration").to_dict("records")
    result = self_brain_diagnose({"readings": readings, "reference_time": "2026-01-01T00:01:55+00:00"})
    assert result["status"] == "ok"
    assert result["machine_id"] == "M-API"
    assert result["human_decision_required"] is True
    assert "telemetry_quality" in result
