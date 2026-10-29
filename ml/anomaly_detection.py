from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

FEATURES = ["temperature_c", "pressure_bar", "vibration_mm_s"]


def load_machine_data(path: str | Path = "data/machine_data.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    _validate_features(df)
    return df


def _validate_contamination(contamination: float) -> None:
    """Validate the Isolation Forest outlier fraction before fitting."""
    if isinstance(contamination, bool) or not isinstance(contamination, (int, float)):
        raise ValueError("contamination must be a number greater than 0 and at most 0.5")
    if not np.isfinite(contamination) or not 0 < contamination <= 0.5:
        raise ValueError("contamination must be greater than 0 and at most 0.5")


def _validate_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return a numeric feature frame or raise a clear, actionable error."""
    if not isinstance(df, pd.DataFrame):
        raise ValueError("telemetry must be provided as a pandas DataFrame")

    missing = [column for column in FEATURES if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required features: {missing}")

    if len(df) < 2:
        raise ValueError("At least 2 telemetry rows are required for anomaly detection")

    try:
        features = df[FEATURES].apply(pd.to_numeric, errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError("Telemetry features must contain numeric values") from exc

    values = features.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Telemetry features must not contain NaN or infinite values")

    return features


def _build_model(contamination: float, random_state: int = 42) -> IsolationForest:
    _validate_contamination(contamination)
    return IsolationForest(contamination=contamination, random_state=random_state)


def detect_anomalies(
    df: pd.DataFrame,
    contamination: float = 0.2,
    random_state: int = 42,
) -> pd.DataFrame:
    """Fit an Isolation Forest and return telemetry with anomaly labels.

    anomaly_label: 1 = normal, -1 = anomalous.
    anomaly_score: higher values indicate more normal observations.

    This is an unsupervised anomaly score, not a calibrated failure probability.
    """
    features = _validate_features(df)
    model = _build_model(contamination, random_state)
    result = df.copy()
    result["anomaly_label"] = model.fit_predict(features)
    result["anomaly_score"] = model.decision_function(features)
    return result


def score_machine_reading(
    reading: dict[str, Any],
    baseline: pd.DataFrame,
    contamination: float = 0.2,
) -> dict[str, float | int | str]:
    """Score one reading against a validated baseline without refitting twice."""
    features = _validate_features(baseline)
    model = _build_model(contamination)
    model.fit(features)

    try:
        row = pd.DataFrame([reading])[FEATURES].apply(pd.to_numeric, errors="raise")
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Reading must include numeric features: {FEATURES}") from exc

    if not np.isfinite(row.to_numpy(dtype=float)).all():
        raise ValueError("Reading features must not contain NaN or infinite values")

    label = int(model.predict(row)[0])
    score = float(model.decision_function(row)[0])

    return {
        "anomaly_label": label,
        "anomaly_score": score,
        "status": "anomalous" if label == -1 else "normal",
    }
