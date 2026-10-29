"""Read-only virtual PLC register map for Self-Brain development.

This is a software simulation only. It does not connect to or write to real PLCs.
"""
from __future__ import annotations

import math
from typing import Any

REQUIRED_FIELDS = (
    "machine_id",
    "temperature_c",
    "pressure_bar",
    "vibration_mm_s",
    "cycle_count",
    "downtime_minutes",
    "fault_code",
)
REGISTER_MAP = {
    "DB1.DBD0": "temperature_c",
    "DB1.DBD4": "pressure_bar",
    "DB1.DBD8": "vibration_mm_s",
    "DB1.DBD12": "cycle_count",
    "DB1.DBD16": "downtime_minutes",
}


def build_virtual_plc_snapshot(reading: dict[str, Any]) -> dict[str, Any]:
    """Convert one validated telemetry reading into a read-only PLC-style snapshot."""
    if not isinstance(reading, dict):
        raise ValueError("reading must be a dictionary")

    missing = [field for field in REQUIRED_FIELDS if field not in reading]
    if missing:
        raise ValueError(f"missing required fields: {missing}")

    machine_id = str(reading["machine_id"]).strip()
    if not machine_id:
        raise ValueError("machine_id cannot be empty")

    numeric: dict[str, float] = {}
    for field in ("temperature_c", "pressure_bar", "vibration_mm_s", "cycle_count", "downtime_minutes"):
        value = reading[field]
        if isinstance(value, bool):
            raise ValueError(f"{field} must be a finite number")
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field} must be a finite number") from None
        if not math.isfinite(number):
            raise ValueError(f"{field} must be a finite number")
        if number < 0:
            raise ValueError(f"{field} cannot be negative")
        numeric[field] = number

    fault_code = str(reading["fault_code"]).strip() or "UNKNOWN"
    if fault_code == "NONE":
        machine_state = "RUNNING"
        alarm_state = "CLEAR"
    elif fault_code.startswith("WARN") or fault_code == "HIGH_TEMP":
        machine_state = "DEGRADED"
        alarm_state = "WARNING"
    else:
        machine_state = "FAULT"
        alarm_state = "ACTIVE"

    registers = {
        address: numeric[field]
        for address, field in REGISTER_MAP.items()
    }
    tags = {
        "MachineId": machine_id,
        "MachineState": machine_state,
        "TemperatureC": numeric["temperature_c"],
        "PressureBar": numeric["pressure_bar"],
        "VibrationMmS": numeric["vibration_mm_s"],
        "CycleCount": int(numeric["cycle_count"]),
        "DowntimeMinutes": numeric["downtime_minutes"],
        "FaultCode": fault_code,
        "AlarmState": alarm_state,
    }
    return {
        "status": "ok",
        "source": "virtual-plc-simulator",
        "machine_id": machine_id,
        "machine_state": machine_state,
        "alarm_state": alarm_state,
        "tags": tags,
        "registers": registers,
        "register_map": REGISTER_MAP.copy(),
        "read_only": True,
        "real_plc_connected": False,
        "write_commands_supported": False,
        "human_decision_required": True,
    }
