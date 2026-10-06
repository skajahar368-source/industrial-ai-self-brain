"""Production monitoring calculations for the industrial simulator.

The calculations are deliberately transparent and deterministic. They are
not a replacement for plant-specific OEE definitions or validated production
systems.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductionSnapshot:
    machine_id: str
    good_count: int
    reject_count: int
    total_count: int
    runtime_minutes: float
    downtime_minutes: float
    ideal_cycle_seconds: float = 5.0

    def metrics(self) -> dict:
        total = max(0, self.total_count)
        runtime = max(0.0, self.runtime_minutes)
        downtime = max(0.0, self.downtime_minutes)
        planned = runtime + downtime
        availability = (runtime / planned * 100.0) if planned else 0.0
        performance = (
            (self.ideal_cycle_seconds * total) / (runtime * 60.0) * 100.0
            if runtime > 0 else 0.0
        )
        quality = (self.good_count / total * 100.0) if total else 0.0
        oee = availability * performance * quality / 10000.0
        return {
            "machine_id": self.machine_id,
            "good_count": max(0, self.good_count),
            "reject_count": max(0, self.reject_count),
            "total_count": total,
            "runtime_minutes": round(runtime, 2),
            "downtime_minutes": round(downtime, 2),
            "availability_percent": round(min(100.0, availability), 2),
            "performance_percent": round(min(100.0, performance), 2),
            "quality_percent": round(min(100.0, quality), 2),
            "oee_percent": round(min(100.0, oee), 2),
        }


def summarize_production(
    *,
    machine_id: str,
    cycle_count: int,
    downtime_minutes: float,
    runtime_minutes: float,
    reject_count: int = 0,
    ideal_cycle_seconds: float = 5.0,
) -> dict:
    if cycle_count < 0 or reject_count < 0:
        raise ValueError("counts cannot be negative")
    if runtime_minutes < 0 or downtime_minutes < 0:
        raise ValueError("time values cannot be negative")
    if ideal_cycle_seconds <= 0:
        raise ValueError("ideal_cycle_seconds must be positive")
    if reject_count > cycle_count:
        raise ValueError("reject_count cannot exceed cycle_count")
    return ProductionSnapshot(
        machine_id=machine_id,
        good_count=cycle_count - reject_count,
        reject_count=reject_count,
        total_count=cycle_count,
        runtime_minutes=runtime_minutes,
        downtime_minutes=downtime_minutes,
        ideal_cycle_seconds=ideal_cycle_seconds,
    ).metrics()
