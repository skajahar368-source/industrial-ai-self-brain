import pandas as pd

from ml.failure_prediction import build_failure_dataset


def row(machine, ts, temp, pressure, vibration, cycles, downtime, fault):
    return {
        "machine_id": machine,
        "timestamp": ts,
        "temperature_c": temp,
        "pressure_bar": pressure,
        "vibration_mm_s": vibration,
        "cycle_count": cycles,
        "downtime_minutes": downtime,
        "fault_code": fault,
    }


def test_labels_future_failure_without_current_fault_leakage():
    frame = pd.DataFrame([
        row("M-001", "2026-09-01T08:00:00Z", 61, 52, 2.8, 100, 0, "NONE"),
        row("M-001", "2026-09-01T09:00:00Z", 63, 54, 3.0, 150, 0, "NONE"),
        row("M-001", "2026-09-01T10:00:00Z", 68, 55, 4.2, 200, 3, "WARN_TEMP"),
        row("M-001", "2026-09-01T11:00:00Z", 82, 56, 7.1, 250, 18, "HIGH_TEMP"),
    ])
    dataset = build_failure_dataset(frame, failure_horizon=1)
    assert len(dataset) == 3
    assert dataset.iloc[0]["failure_within_horizon"] == 0
    assert dataset.iloc[1]["failure_within_horizon"] == 1
    assert "fault_code" not in dataset.columns


def test_machine_histories_are_processed_independently():
    frame = pd.DataFrame([
        row("M-001", "2026-09-01T08:00:00Z", 60, 52, 2.5, 100, 0, "NONE"),
        row("M-001", "2026-09-01T09:00:00Z", 80, 52, 7.0, 150, 10, "HIGH_TEMP"),
        row("M-002", "2026-09-01T08:00:00Z", 60, 52, 2.5, 100, 0, "NONE"),
        row("M-002", "2026-09-01T09:00:00Z", 61, 52, 2.6, 150, 0, "NONE"),
    ])
    dataset = build_failure_dataset(frame)
    assert len(dataset) == 2
    assert dataset["machine_id"].tolist() == ["M-001", "M-002"]
