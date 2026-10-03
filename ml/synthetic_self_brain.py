"""Synthetic machine run-to-failure data for Self-Brain development and validation.

This module deliberately uses the repository's machine telemetry schema. The data is
synthetic and must never be presented as measured industrial performance.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "temperature_c",
    "pressure_bar",
    "vibration_mm_s",
    "downtime_minutes",
    "cycle_count",
]
FAULTS = ("normal", "thermal", "pressure", "vibration", "combined")


def simulate_machine(machine_id: str, rng: np.random.Generator, n_steps: int = 180, fault: str = "normal") -> pd.DataFrame:
    if n_steps < 24:
        raise ValueError("n_steps must be at least 24")
    if fault not in FAULTS:
        raise ValueError(f"unsupported fault: {fault}")

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    failure_onset = int(n_steps * 0.65) if fault != "normal" else None

    for step in range(n_steps):
        progress = step / max(n_steps - 1, 1)
        temperature = 55.0 + 2.0 * progress + rng.normal(0, 0.8)
        pressure = 6.0 + rng.normal(0, 0.12)
        vibration = 2.0 + 0.25 * progress + rng.normal(0, 0.08)
        downtime = max(0.0, rng.normal(0.4, 0.15))
        cycle_count = 1000 + step * 20

        if failure_onset is not None and step >= failure_onset:
            severity = (step - failure_onset + 1) / max(n_steps - failure_onset, 1)
            if fault in ("thermal", "combined"):
                temperature += 18.0 * severity
            if fault in ("pressure", "combined"):
                pressure += 1.8 * severity
            if fault in ("vibration", "combined"):
                vibration += 4.0 * severity
            downtime += 2.0 * severity

        rows.append({
            "timestamp": (start + timedelta(seconds=5 * step)).isoformat(),
            "machine_id": machine_id,
            "temperature_c": round(float(temperature), 4),
            "pressure_bar": round(float(pressure), 4),
            "vibration_mm_s": round(float(vibration), 4),
            "cycle_count": cycle_count,
            "downtime_minutes": round(float(downtime), 4),
            "fault_code": fault,
            "data_origin": "synthetic",
            "rul_steps": (n_steps - 1 - step) if failure_onset is not None and step >= failure_onset else n_steps - failure_onset if failure_onset is not None else n_steps,
        })
    return pd.DataFrame(rows)


def generate_dataset(n_machines: int = 60, seed: int = 7) -> pd.DataFrame:
    if n_machines < len(FAULTS):
        raise ValueError(f"n_machines must be at least {len(FAULTS)}")
    rng = np.random.default_rng(seed)
    frames = []
    for index in range(n_machines):
        fault = FAULTS[index % len(FAULTS)]
        frames.append(simulate_machine(f"M-SYN-{index + 1:03d}", rng, fault=fault))
    return pd.concat(frames, ignore_index=True)
