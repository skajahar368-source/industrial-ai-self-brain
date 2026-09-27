from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ml.failure_model import FailureModel, predict_failure, train_failure_model

MODEL: FailureModel | None = None
METRICS: dict[str, Any] | None = None


def load_training_telemetry(
    machine_data_path: str | Path = "data/machine_data.csv",
    stream_path: str | Path = "data/telemetry_stream.csv",
) -> pd.DataFrame:
    frames = [pd.read_csv(machine_data_path)]
    stream = Path(stream_path)
    if stream.exists() and stream.stat().st_size > 0:
        frames.append(pd.read_csv(stream))
    frame = pd.concat(frames, ignore_index=True)
    return frame.drop_duplicates(subset=["machine_id", "timestamp"], keep="last")


def train_failure_predictor() -> dict[str, Any]:
    global MODEL, METRICS
    from ml.failure_prediction import build_failure_dataset

    telemetry = load_training_telemetry()
    dataset = build_failure_dataset(telemetry)
    MODEL, METRICS = train_failure_model(dataset)
    return {
        "status": "trained",
        "metrics": METRICS,
        "training_samples": len(dataset),
        "feature_columns": MODEL.feature_columns,
        "warning": "Prototype model; validate on representative labeled machine history before operational use.",
    }


def predict_latest(reading: dict[str, Any]) -> dict[str, Any]:
    if MODEL is None:
        return {
            "status": "not_trained",
            "message": "Train the failure predictor before requesting a prediction.",
            "human_decision_required": True,
        }
    return {
        "status": "predicted",
        **predict_failure(MODEL, reading),
        "training_metrics": METRICS,
    }
