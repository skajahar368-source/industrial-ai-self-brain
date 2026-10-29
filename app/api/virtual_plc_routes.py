"""Read-only virtual PLC endpoints, including optional LLM explanations."""
from fastapi import APIRouter

from ml.telemetry_simulator import generate_reading
from ml.virtual_plc import build_virtual_plc_snapshot
from ml.virtual_plc_diagnosis import diagnose_virtual_plc_reading
from ml.virtual_plc_explainer import explain_virtual_plc_diagnosis

router = APIRouter(prefix="/api/virtual-plc", tags=["virtual-plc"])


@router.get("/explain")
def virtual_plc_explain(
    machine_id: str = "M-001",
    step: int = 0,
    scenario: str = "normal",
) -> dict:
    """Explain simulated sensor findings with an optional configured LLM."""
    try:
        reading = generate_reading(machine_id=machine_id, step=step, scenario=scenario)
        snapshot = build_virtual_plc_snapshot(reading)
        diagnosis = diagnose_virtual_plc_reading(reading)
        explanation = explain_virtual_plc_diagnosis(snapshot, diagnosis)
        return {
            "status": "ok",
            "snapshot": snapshot,
            "diagnosis": diagnosis,
            "explanation": explanation,
            "read_only": True,
            "real_plc_connected": False,
            "write_commands_supported": False,
            "human_decision_required": True,
        }
    except (TypeError, ValueError) as exc:
        return {"status": "rejected", "error": str(exc)}
