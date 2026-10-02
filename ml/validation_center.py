from __future__ import annotations

from typing import Any

import pandas as pd

from app.services.health import evaluate_machine_health
from ml.degradation_timeline import build_degradation_timeline
from ml.predictive_maintenance import maintenance_risk
from ml.root_cause import analyze_root_causes
from ml.telemetry_ingestion import normalize_reading
from ml.telemetry_quality import assess_telemetry_quality
from ml.time_series_intelligence import analyze_trends


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
    expected_rejection: bool = False,
) -> dict[str, Any]:
    try:
        normalized = normalize_reading(payload)
    except ValueError as exc:
        passed = expected_rejection
        return {
            "name": name,
            "category": "telemetry_contract",
            "status": "passed" if passed else "failed",
            "expected": "rejected" if expected_rejection else "accepted",
            "actual": "rejected",
            "error": str(exc),
        }

    if expected_rejection:
        return {
            "name": name,
            "category": "telemetry_contract",
            "status": "failed",
            "expected": "rejected",
            "actual": "accepted",
        }

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


def _pipeline_case(name: str, readings: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = [normalize_reading(item) for item in readings]
    trend = analyze_trends(normalized)
    degradation = build_degradation_timeline(normalized)
    root_cause = analyze_root_causes(normalized[-1])
    passed = (
        trend["trend"] == "deteriorating"
        and degradation["direction"] in {"deteriorating", "rapid_deterioration"}
        and root_cause["cause_count"] >= 1
    )
    return {
        "name": name,
        "category": "intelligence_pipeline",
        "status": "passed" if passed else "failed",
        "expected": {
            "trend": "deteriorating",
            "degradation_direction": "deteriorating_or_rapid_deterioration",
            "root_cause_count": ">=1",
        },
        "actual": {
            "trend": trend["trend"],
            "signals": trend["signals"],
            "degradation_direction": degradation["direction"],
            "risk_change": degradation["risk_change"],
            "root_cause_count": root_cause["cause_count"],
        },
    }


def _quality_case() -> dict[str, Any]:
    readings = [
        _reading(
            timestamp="2026-09-27T09:58:00+00:00",
            temperature_c=60.0,
        ),
        _reading(
            timestamp="2026-09-27T10:00:00+00:00",
            temperature_c=85.0,
        ),
        _reading(
            timestamp="2026-09-27T10:00:05+00:00",
            temperature_c=85.0,
        ),
    ]
    quality = assess_telemetry_quality(
        readings,
        reference_time="2026-09-27T10:00:05+00:00",
        stale_after_seconds=60,
        stuck_window=2,
    )
    issue_types = {issue["type"] for issue in quality["issues"]}
    required = {"sudden_spike", "stuck_sensor"}
    passed = quality["quality"] == "degraded" and required.issubset(issue_types)
    return {
        "name": "telemetry_quality",
        "category": "telemetry_quality",
        "status": "passed" if passed else "failed",
        "expected": sorted(required),
        "actual": sorted(issue_types),
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
            expected_rejection=True,
        ),
        _case(
            "invalid_timestamp_rejected",
            _reading(timestamp="not-a-timestamp"),
            expected_rejection=True,
        ),
        _case(
            "missing_required_sensor_rejected",
            {key: value for key, value in _reading().items() if key != "vibration_mm_s"},
            expected_rejection=True,
        ),
        _quality_case(),
        _pipeline_case(
            "degradation_trend_and_root_cause",
            [
                _reading(
                    timestamp="2026-09-27T10:00:00+00:00",
                    temperature_c=60.0,
                    vibration_mm_s=3.0,
                    pressure_bar=55.0,
                ),
                _reading(
                    timestamp="2026-09-27T10:01:00+00:00",
                    temperature_c=70.0,
                    vibration_mm_s=5.0,
                    pressure_bar=65.0,
                ),
                _reading(
                    timestamp="2026-09-27T10:02:00+00:00",
                    temperature_c=84.0,
                    vibration_mm_s=8.5,
                    pressure_bar=105.0,
                    downtime_minutes=30.0,
                    fault_code="MULTI_FAULT",
                ),
            ],
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
