"""Machine-focused ML layer for Industrial AI Self-Brain."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, IsolationForest, RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error
from sklearn.preprocessing import LabelEncoder

from ml.synthetic_self_brain import FEATURE_COLUMNS, generate_dataset

WINDOW = 12


@dataclass
class ModelBundle:
    anomaly: IsolationForest
    classifier: RandomForestClassifier
    rul: HistGradientBoostingRegressor
    encoder: LabelEncoder
    metrics: dict[str, Any]


class SelfBrainML:
    """Train and diagnose machine conditions using the existing telemetry shape.

    Training data is synthetic until representative labeled machine history is supplied.
    Predictions are decision support only; a human maintenance engineer remains responsible
    for the final action.
    """

    def __init__(self, window: int = WINDOW):
        if window < 4:
            raise ValueError("window must be at least 4")
        self.window = window
        self.bundle: ModelBundle | None = None

    def _features(self, readings: list[dict]) -> pd.DataFrame:
        frame = pd.DataFrame(readings)
        missing = [c for c in FEATURE_COLUMNS if c not in frame.columns]
        if missing:
            raise ValueError(f"missing telemetry fields: {missing}")
        frame = frame.copy()
        for col in FEATURE_COLUMNS:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
        if frame[FEATURE_COLUMNS].isna().any().any():
            raise ValueError("telemetry contains non-numeric or missing sensor values")
        if len(frame) < self.window:
            raise ValueError(f"at least {self.window} telemetry readings are required")

        values = {}
        for col in FEATURE_COLUMNS:
            series = frame[col]
            values[f"{col}_mean"] = series.rolling(self.window).mean()
            values[f"{col}_std"] = series.rolling(self.window).std().fillna(0)
            values[f"{col}_slope"] = series.diff(self.window - 1) / max(self.window - 1, 1)
            values[f"{col}_max"] = series.rolling(self.window).max()
        result = pd.DataFrame(values).dropna().reset_index(drop=True)
        return result

    def train(self, seed: int = 7) -> dict[str, Any]:
        data = generate_dataset(seed=seed)
        machine_ids = data["machine_id"].unique()
        rng = np.random.default_rng(seed)
        rng.shuffle(machine_ids)
        split = max(1, int(len(machine_ids) * 0.8))
        train_ids = set(machine_ids[:split])
        train = data[data.machine_id.isin(train_ids)]
        test = data[~data.machine_id.isin(train_ids)]

        X_train, y_fault, y_rul = [], [], []
        X_test, y_fault_test, y_rul_test = [], [], []
        for _, group in train.groupby("machine_id"):
            feats = self._features(group.to_dict("records"))
            start = self.window - 1
            labels = group.iloc[start:]["fault_code"].to_numpy()
            rul = group.iloc[start:]["rul_steps"].to_numpy()
            X_train.append(feats.to_numpy())
            y_fault.extend(labels)
            y_rul.extend(rul)
        for _, group in test.groupby("machine_id"):
            feats = self._features(group.to_dict("records"))
            start = self.window - 1
            X_test.append(feats.to_numpy())
            y_fault_test.extend(group.iloc[start:]["fault_code"].to_numpy())
            y_rul_test.extend(group.iloc[start:]["rul_steps"].to_numpy())

        Xtr = np.vstack(X_train)
        Xte = np.vstack(X_test)
        encoder = LabelEncoder()
        ytr = encoder.fit_transform(y_fault)

        classifier = RandomForestClassifier(n_estimators=180, random_state=seed, class_weight="balanced_subsample")
        classifier.fit(Xtr, ytr)

        anomaly = IsolationForest(n_estimators=160, contamination=0.08, random_state=seed)
        anomaly.fit(Xtr)

        rul = HistGradientBoostingRegressor(max_iter=150, random_state=seed)
        rul.fit(Xtr, np.asarray(y_rul, dtype=float))

        pred = classifier.predict(Xte)
        rul_pred = rul.predict(Xte)
        metrics = {
            "data_origin": "synthetic",
            "warning": "Metrics are synthetic-data validation, not real-machine accuracy.",
            "classification_accuracy": float(accuracy_score(encoder.transform(y_fault_test), pred)),
            "classification_macro_f1": float(f1_score(encoder.transform(y_fault_test), pred, average="macro")),
            "rul_mae_steps": float(mean_absolute_error(y_rul_test, rul_pred)),
            "train_machines": len(train_ids),
            "test_machines": len(machine_ids) - len(train_ids),
            "window": self.window,
        }
        self.bundle = ModelBundle(anomaly, classifier, rul, encoder, metrics)
        return metrics

    def status(self) -> dict[str, Any]:
        return {"trained": self.bundle is not None, "metrics": self.bundle.metrics if self.bundle else None}

    def diagnose(self, readings: list[dict], machine_id: str | None = None) -> dict[str, Any]:
        if self.bundle is None:
            raise ValueError("model is not trained")
        features = self._features(readings)
        latest = features.tail(1).to_numpy()
        predicted_index = int(self.bundle.classifier.predict(latest)[0])
        probabilities = self.bundle.classifier.predict_proba(latest)[0]
        confidence = float(np.max(probabilities))
        anomaly_label = int(self.bundle.anomaly.predict(latest)[0])
        estimated_rul = max(0.0, float(self.bundle.rul.predict(latest)[0]))
        return {
            "status": "ok",
            "machine_id": machine_id or readings[-1].get("machine_id"),
            "predicted_fault": str(self.bundle.encoder.inverse_transform([predicted_index])[0]),
            "confidence": round(confidence, 4),
            "anomaly": anomaly_label == -1,
            "estimated_rul_steps": round(estimated_rul, 2),
            "human_decision_required": True,
            "provenance": "synthetic_training_data",
            "metrics": self.bundle.metrics,
        }
