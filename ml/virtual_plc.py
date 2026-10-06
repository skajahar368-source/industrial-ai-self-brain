"""Vendor-neutral virtual PLC for Self-Brain development and testing.

This module emulates a small PLC register/tag surface without controlling real
industrial equipment. The simulator is deterministic and feeds the existing
machine telemetry schema.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ml.machine_state import MachineStateEngine
from ml.telemetry_simulator import generate_reading


@dataclass
class PLCRegisters:
    machine_id: str
    state: str = "RUNNING"
    mode: str = "AUTO"
    scan_counter: int = 0
    cycle_count: int = 0
    motor_temperature_c: float = 0.0
    pressure_bar: float = 0.0
    vibration_mm_s: float = 0.0
    downtime_minutes: float = 0.0
    fault_code: str = "NONE"
    alarm_active: bool = False
    heartbeat: int = 0


class VirtualPLC:
    """Simple read-only PLC model for the Self-Brain prototype.

    The PLC remains the source of simulated machine state. Self-Brain can read
    the registers, but this class exposes no machine-control write operation.
    """

    def __init__(self, machine_id: str = "M-001", scenario: str = "normal") -> None:
        machine_id = str(machine_id).strip()
        if not machine_id:
            raise ValueError("machine_id cannot be empty")
        self.machine_id = machine_id
        self.scenario = scenario
        self.registers = PLCRegisters(machine_id=machine_id)
        self.state_engine = MachineStateEngine()

    def configure(self, *, scenario: str | None = None, mode: str | None = None) -> dict[str, Any]:
        if scenario is not None:
            scenario = {"warning": "thermal", "failure": "combined"}.get(str(scenario).strip().lower(), str(scenario).strip().lower())
            if scenario not in {"normal", "thermal", "pressure", "vibration", "combined"}:
                raise ValueError("scenario must be one of: ['combined', 'normal', 'pressure', 'thermal', 'vibration']")
            self.scenario = scenario
        if mode is not None:
            mode = str(mode).strip().upper()
            if mode not in {"AUTO", "MANUAL"}:
                raise ValueError("mode must be AUTO or MANUAL")
            self.registers.mode = mode
        return self.snapshot()

    def scan(self) -> dict[str, Any]:
        """Execute one simulated PLC scan and expose the current input tags."""
        step = self.registers.scan_counter
        reading = generate_reading(
            machine_id=self.machine_id,
            step=step,
            scenario=self.scenario,
        )
        self.registers.scan_counter += 1
        self.registers.heartbeat = self.registers.scan_counter
        self.registers.cycle_count = int(reading["cycle_count"])
        self.registers.motor_temperature_c = float(reading["temperature_c"])
        self.registers.pressure_bar = float(reading["pressure_bar"])
        self.registers.vibration_mm_s = float(reading["vibration_mm_s"])
        self.registers.downtime_minutes = float(reading["downtime_minutes"])
        self.registers.fault_code = str(reading["fault_code"])
        self.registers.alarm_active = self.registers.fault_code != "NONE"

        # Deterministic state scoring keeps machine lifecycle separate from ML.
        temp_penalty = max(0.0, self.registers.motor_temperature_c - 70.0) * 1.5
        pressure_penalty = max(0.0, self.registers.pressure_bar - 60.0) * 1.2
        vibration_penalty = max(0.0, self.registers.vibration_mm_s - 4.0) * 8.0
        health_score = 100.0 - temp_penalty - pressure_penalty - vibration_penalty
        if self.scenario == "combined":
            health_score = min(health_score, 30.0)
        elif self.registers.fault_code in {"HIGH_TEMP", "HIGH_PRESSURE", "HIGH_VIBRATION", "MULTI_PARAMETER_FAULT"}:
            health_score = min(health_score, 30.0)
        if self.state_engine.state.value == "OFFLINE":
            self.state_engine.start()
            self.state_engine.complete_startup()
        self.state_engine.evaluate(health_score=health_score, alarm_active=self.registers.alarm_active)
        if self.state_engine.state.value in {"RUNNING", "WARNING", "DEGRADED"}:
            self.state_engine.record_cycle()
        self.registers.cycle_count = self.state_engine.cycles
        self.registers.state = self.state_engine.state.value
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        """Return PLC tags in a stable API-friendly shape."""
        return {
            "machine_id": self.registers.machine_id,
            "state": self.registers.state,
            "mode": self.registers.mode,
            "scenario": self.scenario,
            "scan_counter": self.registers.scan_counter,
            "cycle_count": self.registers.cycle_count,
            "motor_temperature_c": round(self.registers.motor_temperature_c, 2),
            "pressure_bar": round(self.registers.pressure_bar, 2),
            "vibration_mm_s": round(self.registers.vibration_mm_s, 2),
            "downtime_minutes": round(self.registers.downtime_minutes, 2),
            "fault_code": self.registers.fault_code,
            "alarm_active": self.registers.alarm_active,
            "heartbeat": self.registers.heartbeat,
            "state_engine": self.state_engine.snapshot(),
            "read_only_to_self_brain": True,
        }
