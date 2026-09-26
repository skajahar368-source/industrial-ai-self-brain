from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.ensemble import IsolationForest

FEATURES = ["temperature_c", "pressure_bar", "vibration_mm_s"]


def load_machine_data(path: str | Path = "data/machine_data.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [column for column in FEATURES if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required features: {missing}")
    return df


def detect_anomalies(
    df: pd.DataFrame,
    contamination: float = 0.2,
    random_state: int = 42,
) -> pd.DataFrame:
    """Fit an Isolation Forest and return telemetry with anomaly labels.

    anomaly_label: 1 = normal, -1 = anomalous.
    anomaly_score: higher values indicate more normal observations.
    """
    model = IsolationForest(
        contamination=contamination,
        random_state=random_state,
    )
    result = df.copy()
    result["anomaly_label"] = model.fit_predict(result[FEATURES])
    result["anomaly_score"] = model.decision_function(result[FEATURES])
    return result


def score_machine_reading(
    reading: dict[str, float],
    baseline: pd.DataFrame,
    contamination: float = 0.2,
) -> dict[str, float | int | str]:
    scored = detect_anomalies(baseline, contamination=contamination)

    model = IsolationForest(
        contamination=contamination,
        random_state=42,
    )
    model.fit(baseline[FEATURES])

    row = pd.DataFrame([reading])[FEATURES]
    label = int(model.predict(row)[0])
    score = float(model.decision_function(row)[0])

    return {
        "anomaly_label": label,
        "anomaly_score": score,
        "status": "anomalous" if label == -1 else "normal",
    }
