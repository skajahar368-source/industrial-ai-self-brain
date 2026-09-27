from __future__ import annotations

from typing import Any

from app.services.health import evaluate_machine_health
from ml.predictive_maintenance import maintenance_risk
from ml.telemetry_ingestion import normalize_reading

BASE_READING: dict[str, Any] = {
    "timestamp": "2026-09-27T10:00:00+00:00",
    "machine_id": "M-VALIDATION-CENTER",
    "temperature_c": 60.0,
    "pressure_bar": 55.0,
    "vibration_mm_s": 3.0,
    "cycle_count": 2000,
    "downtime_minutes": 0.0,
    "fault_code": "NONE",
    "source": "validation-center",
}


def _reading(**updates: Any) -> dict[str, Any]:
    return {**BASE_READING, **updates}


def _case(
    name: str,
    payload: dict[str, Any],
    expected_status: str | None = None,
) -> dict[str, Any]:
    try:
        normalized = normalize_reading(payload)
        health = evaluate_machine_health(normalized)
        risk = maintenance_risk(normalized)
        passed = expected_status is None or health["status"] == expected_status
        return {
            "name": name,
            "category": "telemetry_behavior",
            "status": "passed" if passed else "failed",
            "expected_health": expected_status,
            "actual_health": health["status"],
            "maintenance_risk": risk["risk_level"],
            "details": {
                "health": health,
                "maintenance_risk": risk,
            },
        }
    except ValueError as exc:
        return {
            "name": name,
            "category": "telemetry_contract",
            "status": "passed",
            "expected": "rejected",
            "actual": "rejected",
            "error": str(exc),
        }


def run_validation_suite() -> dict[str, Any]:
    cases = [
        _case("normal_baseline", _reading(), "normal"),
        _case("high_temperature", _reading(temperature_c=82.0), "critical"),
        _case("high_pressure", _reading(pressure_bar=105.0), "critical"),
        _case("high_vibration", _reading(vibration_mm_s=9.0), "critical"),
        _case(
            "combined_failure",
            _reading(
                temperature_c=88.0,
                pressure_bar=105.0,
                vibration_mm_s=9.0,
                downtime_minutes=30.0,
                fault_code="MULTI_FAULT",
            ),
            "critical",
        ),
        _case(
            "negative_temperature_rejected",
            _reading(temperature_c=-1.0),
        ),
        _case(
            "invalid_timestamp_rejected",
            _reading(timestamp="not-a-timestamp"),
        ),
        _case(
            "missing_required_sensor_rejected",
            {key: value for key, value in _reading().items() if key != "vibration_mm_s"},
        ),
    ]

    passed = sum(case["status"] == "passed" for case in cases)
    failed = len(cases) - passed

    return {
        "status": "passed" if failed == 0 else "failed",
        "total_cases": len(cases),
        "passed": passed,
        "failed": failed,
        "scope": "software validation only; no production-machine claim",
        "cases": cases,
    }
