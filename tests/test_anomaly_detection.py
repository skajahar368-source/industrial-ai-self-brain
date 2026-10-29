import numpy as np
import pandas as pd
import pytest

from ml.anomaly_detection import detect_anomalies, score_machine_reading


def sample_data():
    return pd.DataFrame(
        {
            "temperature_c": [50, 51, 52, 53, 95],
            "pressure_bar": [50, 51, 52, 53, 110],
            "vibration_mm_s": [2, 2.1, 2.2, 2.1, 10],
        }
    )


def test_anomaly_detection_adds_model_columns():
    result = detect_anomalies(sample_data(), contamination=0.2)

    assert "anomaly_label" in result.columns
    assert "anomaly_score" in result.columns
    assert -1 in result["anomaly_label"].values


@pytest.mark.parametrize("contamination", [0, -0.1, 0.6, float("nan"), float("inf")])
def test_rejects_invalid_contamination(contamination):
    with pytest.raises(ValueError, match="contamination"):
        detect_anomalies(sample_data(), contamination=contamination)


def test_rejects_missing_feature():
    data = sample_data().drop(columns=["vibration_mm_s"])

    with pytest.raises(ValueError, match="Missing required features"):
        detect_anomalies(data)


def test_rejects_too_few_rows():
    with pytest.raises(ValueError, match="At least 2 telemetry rows"):
        detect_anomalies(sample_data().head(1))


@pytest.mark.parametrize("bad_value", [np.nan, np.inf, -np.inf])
def test_rejects_non_finite_sensor_values(bad_value):
    data = sample_data()
    data.loc[0, "temperature_c"] = bad_value

    with pytest.raises(ValueError, match="NaN or infinite"):
        detect_anomalies(data)


def test_rejects_non_numeric_sensor_values():
    data = sample_data()
    data["temperature_c"] = data["temperature_c"].astype(object)
    data.loc[0, "temperature_c"] = "sensor-error"

    with pytest.raises(ValueError, match="numeric values"):
        detect_anomalies(data)


def test_score_machine_reading_returns_structured_result():
    result = score_machine_reading(
        {
            "temperature_c": 95,
            "pressure_bar": 110,
            "vibration_mm_s": 10,
        },
        sample_data(),
    )

    assert result["anomaly_label"] in (-1, 1)
    assert isinstance(result["anomaly_score"], float)
    assert result["status"] in ("normal", "anomalous")


def test_score_machine_reading_rejects_missing_feature():
    with pytest.raises(ValueError, match="must include numeric features"):
        score_machine_reading({"temperature_c": 95}, sample_data())
