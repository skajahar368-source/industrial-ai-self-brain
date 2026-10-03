import pytest

from ml.self_brain_ml import SelfBrainML
from ml.synthetic_self_brain import simulate_machine


def test_self_brain_trains_on_synthetic_machine_data():
    model = SelfBrainML()
    metrics = model.train()
    assert metrics["data_origin"] == "synthetic"
    assert 0 <= metrics["classification_accuracy"] <= 1
    assert metrics["rul_mae_steps"] >= 0


def test_self_brain_diagnoses_existing_machine_telemetry_shape():
    import numpy as np

    model = SelfBrainML()
    model.train()
    readings = simulate_machine("M-TEST", np.random.default_rng(1), n_steps=30, fault="vibration").to_dict("records")
    result = model.diagnose(readings, machine_id="M-TEST")
    assert result["status"] == "ok"
    assert result["human_decision_required"] is True
    assert result["machine_id"] == "M-TEST"
