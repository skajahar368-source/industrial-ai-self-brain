"""Self-Brain model diagnosis with an optional grounded LLM explanation."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ml.self_brain_ml import SelfBrainML
from ml.telemetry_quality import assess_telemetry_quality
from ml.virtual_plc import build_virtual_plc_snapshot
from ml.virtual_plc_diagnosis import diagnose_virtual_plc_reading
from ml.virtual_plc_explainer import explain_virtual_plc_diagnosis

router = APIRouter(prefix="/api/self-brain", tags=["self-brain"])
_EXPLAINER_BRAIN: SelfBrainML | None = None
MAX_READINGS = 500


@router.post("/diagnose/explain")
def self_brain_diagnose_explain(payload: dict[str, Any]) -> dict[str, Any]:
    """Analyze supplied telemetry, then optionally explain findings using an LLM.

    This endpoint is read-only decision support. It does not connect to or command a PLC.
    The model was trained on synthetic data unless the training implementation changes.
    """
    global _EXPLAINER_BRAIN
    readings = payload.get("readings")
    if not isinstance(readings, list) or not readings:
        return {"status": "rejected", "error": "readings must be a non-empty list"}
    if len(readings) > MAX_READINGS:
        return {"status": "rejected", "error": f"readings cannot exceed {MAX_READINGS} items"}
    if any(not isinstance(item, dict) for item in readings):
        return {"status": "rejected", "error": "each reading must be a dictionary"}

    try:
        quality = assess_telemetry_quality(
            readings,
            reference_time=payload.get("reference_time"),
            stale_after_seconds=int(payload.get("stale_after_seconds", 60)),
        )
        blocking = {"invalid_timestamp", "missing_sensor"}
        if any(issue["type"] in blocking for issue in quality["issues"]):
            return {
                "status": "rejected",
                "reason": "telemetry_quality",
                "telemetry_quality": quality,
                "read_only": True,
                "real_plc_connected": False,
                "write_commands_supported": False,
            }

        latest = readings[-1]
        snapshot = build_virtual_plc_snapshot(latest)
        rule_diagnosis = diagnose_virtual_plc_reading(latest)

        if _EXPLAINER_BRAIN is None:
            _EXPLAINER_BRAIN = SelfBrainML()
            _EXPLAINER_BRAIN.train()
        ml_diagnosis = _EXPLAINER_BRAIN.diagnose(
            readings,
            machine_id=payload.get("machine_id") or latest.get("machine_id"),
        )
        combined_findings = {
            "analysis_type": "rules_plus_ml",
            "rule_based_diagnosis": rule_diagnosis,
            "ml_diagnosis": ml_diagnosis,
            "telemetry_quality": quality,
        }
        explanation = explain_virtual_plc_diagnosis(snapshot, combined_findings)
        return {
            "status": "ok",
            "snapshot": snapshot,
            "rule_based_diagnosis": rule_diagnosis,
            "ml_diagnosis": ml_diagnosis,
            "telemetry_quality": quality,
            "explanation": explanation,
            "data_provenance": "provided_telemetry; model trained on synthetic data",
            "read_only": True,
            "real_plc_connected": False,
            "write_commands_supported": False,
            "human_decision_required": True,
        }
    except (TypeError, ValueError) as exc:
        return {
            "status": "rejected",
            "error": str(exc),
            "read_only": True,
            "real_plc_connected": False,
            "write_commands_supported": False,
        }
