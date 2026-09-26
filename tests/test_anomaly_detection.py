import pandas as pd

from ml.anomaly_detection import detect_anomalies


def test_anomaly_detection_adds_model_columns():
    df = pd.DataFrame(
        {
            "temperature_c": [50, 51, 52, 53, 95],
            "pressure_bar": [50, 51, 52, 53, 110],
            "vibration_mm_s": [2, 2.1, 2.2, 2.1, 10],
        }
    )

    result = detect_anomalies(df, contamination=0.2)

    assert "anomaly_label" in result.columns
    assert "anomaly_score" in result.columns
    assert -1 in result["anomaly_label"].values
