from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

SCENARIOS = {"normal", "warning", "failure"}


def generate_reading(
    machine_id: str = "M-001",
    step: int = 0,
    scenario: str = "normal",
    interval_seconds: int = 5,
) -> dict[str, Any]:
    """Generate deterministic machine telemetry for controlled simulation."""
    scenario = scenario.lower().strip()
    if scenario not in SCENARIOS:
        raise ValueError(f"scenario must be one of: {sorted(SCENARIOS)}")
    if step < 0:
        raise ValueError("step cannot be negative")
    if interval_seconds < 1:
        raise ValueError("interval_seconds must be positive")

    progress = min(step, 20)
    if scenario == "normal":
        temperature = 61.0 + 0.15 * progress
        pressure = 52.0 + 0.1 * progress
        vibration = 2.8 + 0.05 * progress
        downtime = 0.0
        fault = "NONE"
    elif scenario == "warning":
        temperature = 65.0 + 0.8 * progress
        pressure = 55.0 + 0.2 * progress
        vibration = 4.5 + 0.3 * progress
        downtime = min(15.0, 1.0 + progress * 0.7)
        fault = "WARN_TEMP" if progress < 12 else "HIGH_TEMP"
    else:
        temperature = 80.0 + 0.35 * progress
        pressure = 100.0 + 0.25 * progress
        vibration = 8.0 + 0.2 * progress
        downtime = min(60.0, 20.0 + progress * 1.5)
        fault = "HIGH_TEMP_PRESSURE"

    timestamp = datetime.now(timezone.utc) + timedelta(seconds=step * interval_seconds)
    return {
        "timestamp": timestamp.isoformat(),
        "machine_id": machine_id,
        "temperature_c": round(temperature, 2),
        "pressure_bar": round(pressure, 2),
        "vibration_mm_s": round(vibration, 2),
        "cycle_count": 1000 + step * 50,
        "downtime_minutes": round(downtime, 2),
        "fault_code": fault,
        "source": "self-brain-simulator",
        "sequence_id": f"SIM-{machine_id}-{scenario}-{step}",
    }


def generate_batch(
    machine_id: str = "M-001",
    start_step: int = 0,
    count: int = 10,
    scenario: str = "normal",
    interval_seconds: int = 5,
) -> list[dict[str, Any]]:
    if count < 1 or count > 500:
        raise ValueError("count must be between 1 and 500")
    return [
        generate_reading(
            machine_id=machine_id,
            step=start_step + offset,
            scenario=scenario,
            interval_seconds=interval_seconds,
        )
        for offset in range(count)
    ]
