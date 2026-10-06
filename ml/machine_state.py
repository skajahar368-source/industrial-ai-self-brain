"""Deterministic industrial machine state engine for the virtual PLC.

This module models machine lifecycle/state transitions independently from
the ML layer. It is intentionally vendor-neutral and simulation-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MachineState(str, Enum):
    OFFLINE = "OFFLINE"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    FAULT = "FAULT"
    STOPPING = "STOPPING"
    MAINTENANCE = "MAINTENANCE"


@dataclass
class MachineStateEngine:
    """State machine driven by health, alarm, and operator events."""

    state: MachineState = MachineState.OFFLINE
    cycles: int = 0
    transitions: int = 0

    def start(self) -> MachineState:
        if self.state in {MachineState.OFFLINE, MachineState.STOPPING}:
            self.state = MachineState.STARTING
            self.transitions += 1
        return self.state

    def complete_startup(self) -> MachineState:
        if self.state == MachineState.STARTING:
            self.state = MachineState.RUNNING
            self.transitions += 1
        return self.state

    def evaluate(self, *, health_score: float = 100.0, alarm_active: bool = False) -> MachineState:
        """Update operating state from deterministic machine signals."""
        score = max(0.0, min(100.0, float(health_score)))
        if self.state == MachineState.MAINTENANCE:
            return self.state
        if alarm_active and score < 35:
            target = MachineState.FAULT
        elif score < 55:
            target = MachineState.DEGRADED
        elif score < 75 or alarm_active:
            target = MachineState.WARNING
        elif self.state in {MachineState.STARTING, MachineState.OFFLINE}:
            target = MachineState.RUNNING
        else:
            target = MachineState.RUNNING
        if target != self.state:
            self.state = target
            self.transitions += 1
        return self.state

    def record_cycle(self) -> int:
        if self.state in {MachineState.RUNNING, MachineState.WARNING, MachineState.DEGRADED}:
            self.cycles += 1
        return self.cycles

    def request_stop(self) -> MachineState:
        if self.state not in {MachineState.OFFLINE, MachineState.MAINTENANCE}:
            self.state = MachineState.STOPPING
            self.transitions += 1
        return self.state

    def enter_maintenance(self) -> MachineState:
        self.state = MachineState.MAINTENANCE
        self.transitions += 1
        return self.state

    def complete_maintenance(self) -> MachineState:
        self.state = MachineState.OFFLINE
        self.transitions += 1
        return self.state

    def snapshot(self) -> dict:
        return {
            "state": self.state.value,
            "cycle_count": self.cycles,
            "transition_count": self.transitions,
        }
