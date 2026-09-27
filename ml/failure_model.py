from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score


@dataclass
class FailureModel:
    model: RandomForestClassifier
    feature_columns: list[str]


def train_failure_model(dataset: pd.DataFrame) -> tuple[FailureModel, dict[str, Any]]:
    feature_columns = [
        "temperature_c",
        "pressure_bar",
        "vibration_mm_s",
        "cycle_count",
        "downtime_minutes",
    ]
    if len(dataset) < 4:
        raise ValueError("at least 4 labeled samples are required")
    if dataset["failure_within_horizon"].nunique() < 2:
        raise ValueError("training data must contain both failure classes")

    frame = dataset.sort_values("timestamp").reset_index(drop=True)
    split = max(2, int(len(frame) * 0.8))
    if split >= len(frame):
        split = len(frame) - 1

    train = frame.iloc[:split]
    test = frame.iloc[split:]
    if train["failure_within_horizon"].nunique() < 2:
        raise ValueError("time-based training split must contain both failure classes")

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(train[feature_columns], train["failure_within_horizon"])

    predictions = model.predict(test[feature_columns])
    probabilities = model.predict_proba(test[feature_columns])[:, 1]
    metrics: dict[str, Any] = {
        "train_samples": len(train),
        "test_samples": len(test),
        "accuracy": round(float(accuracy_score(test["failure_within_horizon"], predictions)), 4),
        "precision": round(float(precision_score(test["failure_within_horizon"], predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(test["failure_within_horizon"], predictions, zero_division=0)), 4),
        "roc_auc": None,
    }
    if test["failure_within_horizon"].nunique() == 2:
        metrics["roc_auc"] = round(float(roc_auc_score(test["failure_within_horizon"], probabilities)), 4)
    return FailureModel(model=model, feature_columns=feature_columns), metrics


def predict_failure(model: FailureModel, reading: dict[str, Any]) -> dict[str, Any]:
    features = pd.DataFrame([{column: float(reading[column]) for column in model.feature_columns}])
    probability = float(model.model.predict_proba(features)[0, 1])
    return {
        "failure_probability": round(probability, 4),
        "risk_band": "high" if probability >= 0.7 else "medium" if probability >= 0.4 else "low",
        "model_type": "RandomForestClassifier",
        "human_decision_required": True,
    }
