import pandas as pd
import pytest

from ml.failure_model import predict_failure, train_failure_model


def dataset():
    rows = []
    for i in range(10):
        failing = i >= 5
        rows.append({
            "timestamp": f"2026-09-{i+1:02d}T00:00:00Z",
            "temperature_c": 60 + i * 4,
            "pressure_bar": 52 + i * 4,
            "vibration_mm_s": 2.5 + i * 0.9,
            "cycle_count": 1000 + i * 100,
            "downtime_minutes": i * 3,
            "failure_within_horizon": int(failing),
        })
    return pd.DataFrame(rows)


def test_failure_model_uses_time_based_evaluation():
    model, metrics = train_failure_model(dataset())
    assert metrics["train_samples"] == 8
    assert metrics["test_samples"] == 2
    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics


def test_failure_prediction_returns_probability_and_human_gate():
    model, _ = train_failure_model(dataset())
    result = predict_failure(model, {
        "temperature_c": 88,
        "pressure_bar": 80,
        "vibration_mm_s": 9,
        "cycle_count": 2200,
        "downtime_minutes": 25,
    })
    assert 0 <= result["failure_probability"] <= 1
    assert result["risk_band"] in {"low", "medium", "high"}
    assert result["human_decision_required"] is True


def test_training_rejects_single_class_data():
    frame = dataset()
    frame["failure_within_horizon"] = 0
    with pytest.raises(ValueError, match="both failure classes"):
        train_failure_model(frame)
