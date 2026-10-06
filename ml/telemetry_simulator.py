from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

SCENARIOS = {"normal", "thermal", "pressure", "vibration", "combined"}


def generate_reading(machine_id: str = "M-001", step: int = 0, scenario: str = "normal", interval_seconds: int = 5) -> dict[str, Any]:
    """Generate deterministic industrial telemetry for controlled fault injection."""
    scenario = scenario.lower().strip()
    if scenario not in SCENARIOS:
        raise ValueError(f"scenario must be one of: {sorted(SCENARIOS)}")
    if step < 0:
        raise ValueError("step cannot be negative")
    if interval_seconds < 1:
        raise ValueError("interval_seconds must be positive")

    progress = min(step, 40)
    base_temperature = 61.0 + 0.12 * progress
    base_pressure = 52.0 + 0.08 * progress
    base_vibration = 2.8 + 0.04 * progress
    downtime = 0.0
    fault = "NONE"

    if scenario == "normal":
        temperature, pressure, vibration = base_temperature, base_pressure, base_vibration
    elif scenario == "thermal":
        severity = max(0, progress - 5)
        temperature = base_temperature + 0.95 * severity
        pressure, vibration = base_pressure, base_vibration
        downtime = min(30.0, severity * 0.45)
        fault = "THERMAL_DEGRADATION" if severity < 15 else "HIGH_TEMP"
    elif scenario == "pressure":
        severity = max(0, progress - 5)
        temperature = base_temperature + 0.15 * severity
        pressure = base_pressure + 1.65 * severity
        vibration = base_vibration + 0.08 * severity
        downtime = min(30.0, severity * 0.5)
        fault = "PRESSURE_DEGRADATION" if severity < 18 else "HIGH_PRESSURE"
    elif scenario == "vibration":
        severity = max(0, progress - 5)
        temperature = base_temperature + 0.25 * severity
        pressure = base_pressure
        vibration = base_vibration + 0.42 * severity
        downtime = min(30.0, severity * 0.6)
        fault = "VIBRATION_DEGRADATION" if severity < 12 else "HIGH_VIBRATION"
    else:
        severity = max(0, progress - 5)
        temperature = base_temperature + 0.65 * severity
        pressure = base_pressure + 1.1 * severity
        vibration = base_vibration + 0.32 * severity
        downtime = min(60.0, severity * 1.1)
        fault = "COMBINED_DEGRADATION" if severity < 12 else "MULTI_PARAMETER_FAULT"

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


def generate_batch(machine_id: str = "M-001", start_step: int = 0, count: int = 10, scenario: str = "normal", interval_seconds: int = 5) -> list[dict[str, Any]]:
    if count < 1 or count > 500:
        raise ValueError("count must be between 1 and 500")
    return [generate_reading(machine_id, start_step + offset, scenario, interval_seconds) for offset in range(count)]
