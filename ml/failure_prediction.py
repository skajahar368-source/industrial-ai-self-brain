from __future__ import annotations

from typing import Any

import pandas as pd


FEATURE_COLUMNS = [
    "temperature_c",
    "pressure_bar",
    "vibration_mm_s",
    "cycle_count",
    "downtime_minutes",
]


def build_failure_dataset(
    telemetry: pd.DataFrame,
    failure_horizon: int = 1,
) -> pd.DataFrame:
    """Build supervised samples where the label means failure in a future window.

    A failure is represented by a non-NONE fault code. The current row is never
    used as its own target, preventing direct leakage from the fault code.
    """
    if failure_horizon < 1:
        raise ValueError("failure_horizon must be positive")

    missing = [c for c in FEATURE_COLUMNS + ["machine_id", "timestamp", "fault_code"] if c not in telemetry]
    if missing:
        raise ValueError(f"missing columns: {missing}")

    frame = telemetry.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
    frame = frame.dropna(subset=["timestamp"]).sort_values(["machine_id", "timestamp"])

    rows: list[dict[str, Any]] = []
    for _, group in frame.groupby("machine_id", sort=False):
        group = group.reset_index(drop=True)
        for index in range(len(group) - failure_horizon):
            current = group.iloc[index]
            future = group.iloc[index + 1 : index + 1 + failure_horizon]
            future_failure = (future["fault_code"].astype(str).str.upper() != "NONE").any()
            row = {column: current[column] for column in FEATURE_COLUMNS}
            row["machine_id"] = current["machine_id"]
            row["timestamp"] = current["timestamp"]
            row["failure_within_horizon"] = int(future_failure)
            rows.append(row)

    return pd.DataFrame(rows, columns=FEATURE_COLUMNS + ["machine_id", "timestamp", "failure_within_horizon"])
