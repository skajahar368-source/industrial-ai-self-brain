from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter

from app.services.health import evaluate_machine_health
from ml.anomaly_detection import detect_anomalies
from ml.historical_diagnosis import diagnose_against_history
from ml.industrial_assistant import ask_industrial_assistant
from ml.telemetry_ingestion import ingest_batch, ingest_reading, recent_telemetry
from ml.telemetry_quality import assess_telemetry_quality
from ml.time_series_intelligence import analyze_trends
from ml.validation_center import run_validation_suite
from ml.degradation_timeline import build_degradation_timeline
from ml.telemetry_simulator import generate_batch, generate_reading
from ml.failure_prediction_service import predict_latest, train_failure_predictor
from ml.failure_pattern_learning import (
    build_failure_patterns,
    learn_failure_pattern,
    record_learning_outcome,
    summarize_learning_outcomes,
)
from ml.part_lifecycle import active_part_life
from ml.predictive_maintenance import maintenance_risk, score_dataframe
from ml.plc_gateway import PLCGateway
from ml.virtual_plc import VirtualPLC
from ml.replacement_workflow import validate_early_replacement
from ml.root_cause import analyze_root_causes
from ml.spare_management import analyze_inventory, spare_status
from ml.self_brain_ml import SelfBrainML

_SELF_BRAIN: SelfBrainML | None = None
_PLC_GATEWAYS: dict[str, PLCGateway] = {}

router = APIRouter(prefix="/api")
DATA_PATH = Path("data/machine_data.csv")
SPARES_PATH = Path("data/spare_parts.csv")
PART_HISTORY_PATH = Path("data/part_replacement_history.csv")


@router.get("/health")
def api_health() -> dict:
    return {"status": "healthy"}


def _get_plc_gateway(machine_id: str = "M-001", scenario: str | None = None) -> PLCGateway:
    machine_id = str(machine_id).strip()
    if not machine_id:
        raise ValueError("machine_id cannot be empty")
    gateway = _PLC_GATEWAYS.get(machine_id)
    if gateway is None:
        gateway = PLCGateway(VirtualPLC(machine_id=machine_id, scenario=scenario or "normal"))
        _PLC_GATEWAYS[machine_id] = gateway
    elif scenario is not None:
        gateway.configure(scenario=scenario)
    return gateway


@router.get("/plc/status")
def plc_status(machine_id: str = "M-001") -> dict:
    try:
        return {"status": "ok", "plc": _get_plc_gateway(machine_id).plc.snapshot()}
    except ValueError as exc:
        return {"status": "rejected", "error": str(exc)}


@router.post("/plc/configure")
def plc_configure(payload: dict) -> dict:
    try:
        gateway = _get_plc_gateway(
            machine_id=str(payload.get("machine_id", "M-001")),
        )
        return {
            "status": "configured",
            "plc": gateway.configure(
                scenario=payload.get("scenario"),
                mode=payload.get("mode"),
            ),
        }
    except ValueError as exc:
        return {"status": "rejected", "error": str(exc)}


@router.post("/plc/scan")
def plc_scan(payload: dict) -> dict:
    try:
        gateway = _get_plc_gateway(
            machine_id=str(payload.get("machine_id", "M-001")),
            scenario=payload.get("scenario"),
        )
        return {"status": "ok", **gateway.scan()}
    except (TypeError, ValueError) as exc:
        return {"status": "rejected", "error": str(exc)}


@router.post("/simulator/demo")
def simulator_demo(payload: dict) -> dict:
    """Run a complete virtual-machine degradation demo through the PLC gateway."""
    global _SELF_BRAIN
    try:
        machine_id = str(payload.get("machine_id", "M-DEMO")).strip()
        scenario = str(payload.get("scenario", "thermal")).strip().lower()
        count = int(payload.get("count", 24))
        if count < 12 or count > 120:
            raise ValueError("count must be between 12 and 120")
        gateway = _get_plc_gateway(machine_id=machine_id, scenario=scenario)
        scans = []
        for _ in range(count):
            scans.append(gateway.scan())
        readings = recent_telemetry(machine_id=machine_id, limit=count)
        latest = readings[0]
        health = evaluate_machine_health(latest)
        quality = assess_telemetry_quality(readings, stale_after_seconds=60)
        risk = maintenance_risk(latest)
        root_cause = analyze_root_causes(latest)
        if _SELF_BRAIN is None:
            _SELF_BRAIN = SelfBrainML()
            _SELF_BRAIN.train()
        brain = _SELF_BRAIN.diagnose(readings, machine_id=machine_id)
        return {
            "status": "ok",
            "demo": {
                "machine_id": machine_id,
                "scenario": scenario,
                "samples": len(readings),
                "description": "Synthetic degradation run through the VirtualPLC and read-only gateway.",
            },
            "plc": scans[-1]["plc"],
            "latest_telemetry": latest,
            "telemetry_quality": quality,
            "health": health,
            "maintenance_risk": risk,
            "root_cause": root_cause,
            "brain": brain,
            "control_write_performed": False,
        }
    except (TypeError, ValueError) as exc:
        return {"status": "rejected", "error": str(exc)}


@router.post("/gateway/scan")
def gateway_scan(payload: dict) -> dict:
    """Read PLC -> ingest telemetry -> run Self-Brain decision support.

    This endpoint deliberately performs no PLC control write. It is the first
    end-to-end bridge between the virtual PLC and the existing ML layer.
    """
    global _SELF_BRAIN
    try:
        gateway = _get_plc_gateway(
            machine_id=str(payload.get("machine_id", "M-001")),
            scenario=payload.get("scenario"),
        )
        scanned = gateway.scan()
        machine_id = scanned["plc"]["machine_id"]
        readings = recent_telemetry(machine_id=machine_id, limit=20)
        latest = readings[0]
        quality = assess_telemetry_quality(
            readings,
            reference_time=payload.get("reference_time"),
            stale_after_seconds=int(payload.get("stale_after_seconds", 60)),
        )
        health = evaluate_machine_health(latest)
        risk = maintenance_risk(latest)

        brain: dict[str, Any]
        if len(readings) < 12:
            brain = {
                "status": "warming_up",
                "reason": "Self-Brain requires at least 12 telemetry readings for its current window.",
                "readings_available": len(readings),
            }
        else:
            blocking = {"invalid_timestamp", "missing_sensor"}
            blocking_issues = [issue for issue in quality["issues"] if issue["type"] in blocking]
            if blocking_issues:
                brain = {
                    "status": "blocked",
                    "reason": "telemetry_quality",
                    "quality": quality,
                }
            else:
                if _SELF_BRAIN is None:
                    _SELF_BRAIN = SelfBrainML()
                    _SELF_BRAIN.train()
                brain = _SELF_BRAIN.diagnose(readings, machine_id=machine_id)

        return {
            "status": "ok",
            "pipeline": "PLC -> Gateway -> Telemetry -> Health/Risk -> Self-Brain",
            "plc": scanned["plc"],
            "telemetry": scanned["telemetry"],
            "ingestion": scanned["ingestion"],
            "telemetry_quality": quality,
            "health": health,
            "maintenance_risk": risk,
            "brain": brain,
            "control_write_performed": False,
        }
    except (TypeError, ValueError) as exc:
        return {"status": "rejected", "error": str(exc)}


@router.post("/telemetry/quality")
def telemetry_quality(payload: dict) -> dict:
    readings = payload.get("readings", [])
    if not isinstance(readings, list):
        return {"status": "rejected", "error": "readings must be a list"}
    try:
        return assess_telemetry_quality(
            readings,
            reference_time=payload.get("reference_time"),
            stale_after_seconds=int(payload.get("stale_after_seconds", 60)),
            stuck_window=int(payload.get("stuck_window", 3)),
            spike_thresholds=payload.get("spike_thresholds"),
        )
    except (TypeError, ValueError) as exc:
        return {"status": "rejected", "error": str(exc)}


@router.post("/telemetry/ingest")
def telemetry_ingest(payload: dict) -> dict:
    try:
        return ingest_reading(payload)
    except ValueError as exc:
        return {"status": "rejected", "error": str(exc)}


@router.post("/telemetry/ingest-batch")
def telemetry_ingest_batch(payload: list[dict]) -> dict:
    return ingest_batch(payload)


@router.post("/telemetry/simulate")
def telemetry_simulate(payload: dict) -> dict:
    try:
        reading = generate_reading(
            machine_id=str(payload.get("machine_id", "M-001")),
            step=int(payload.get("step", 0)),
            scenario=str(payload.get("scenario", "normal")),
            interval_seconds=int(payload.get("interval_seconds", 5)),
        )
        return ingest_reading(reading)
    except (TypeError, ValueError) as exc:
        return {"status": "rejected", "error": str(exc)}


@router.post("/telemetry/simulate-batch")
def telemetry_simulate_batch(payload: dict) -> dict:
    try:
        readings = generate_batch(
            machine_id=str(payload.get("machine_id", "M-001")),
            start_step=int(payload.get("start_step", 0)),
            count=int(payload.get("count", 10)),
            scenario=str(payload.get("scenario", "normal")),
            interval_seconds=int(payload.get("interval_seconds", 5)),
        )
        return ingest_batch(readings)
    except (TypeError, ValueError) as exc:
        return {"status": "rejected", "error": str(exc)}


@router.get("/telemetry")
def telemetry(machine_id: str | None = None, limit: int = 20) -> dict:
    try:
        records = recent_telemetry(machine_id=machine_id, limit=limit)
    except ValueError as exc:
        return {"status": "rejected", "error": str(exc)}
    return {"count": len(records), "telemetry": records}


@router.post("/failure-model/train")
def failure_model_train() -> dict:
    try:
        return train_failure_predictor()
    except ValueError as exc:
        return {"status": "rejected", "error": str(exc)}


@router.post("/failure-prediction")
def failure_prediction(payload: dict) -> dict:
    return predict_latest(payload)


@router.post("/assistant/ask")
def industrial_assistant(payload: dict) -> dict:
    return ask_industrial_assistant(payload)


@router.get("/validation/run")
def validation_run() -> dict:
    """Run the deterministic software validation suite without storing telemetry."""
    return run_validation_suite()


@router.get("/dashboard/overview")
def dashboard_overview(machine_id: str = "M-001") -> dict:
    """Return one read-only snapshot for the dashboard control room."""
    telemetry_records = recent_telemetry(machine_id=machine_id, limit=20)
    trend_analysis = analyze_trends(telemetry_records)
    degradation_timeline = build_degradation_timeline(telemetry_records)
    if telemetry_records:
        latest = telemetry_records[0]
    else:
        source = pd.read_csv(DATA_PATH)
        machine_rows = source[source["machine_id"] == machine_id]
        if machine_rows.empty:
            return {"status": "not_found", "machine_id": machine_id}
        latest = machine_rows.sort_values("timestamp", ascending=False).iloc[0].to_dict()

    health = evaluate_machine_health(latest)
    risk = maintenance_risk(latest)
    baseline = pd.read_csv(DATA_PATH)
    anomaly = detect_anomalies(baseline)
    machine_anomalies = anomaly[anomaly["machine_id"] == machine_id]
    latest_anomaly = (
        machine_anomalies.sort_values("timestamp", ascending=False).iloc[0].to_dict()
        if not machine_anomalies.empty
        else {}
    )
    root_cause = analyze_root_causes(latest)
    spare_df = analyze_inventory(pd.read_csv(SPARES_PATH))
    spare_alerts_df = spare_df[spare_df["status"].isin(["out_of_stock", "reorder", "low"])]

    return {
        "status": "ok",
        "machine_id": machine_id,
        "latest_telemetry": latest,
        "health": health,
        "maintenance_risk": risk,
        "anomaly": {
            "anomaly_label": latest_anomaly.get("anomaly_label"),
            "anomaly_score": latest_anomaly.get("anomaly_score"),
            "status": "anomalous" if latest_anomaly.get("anomaly_label") == -1 else "normal",
        },
        "root_cause": root_cause,
        "spare_alerts": spare_alerts_df[
            ["spare_id", "part_name", "status", "stock_quantity", "critical", "action"]
        ].to_dict(orient="records"),
        "recent_telemetry": telemetry_records[:10],
        "trend_analysis": trend_analysis,
        "degradation_timeline": degradation_timeline,
    }


@router.post("/machine-health")
def machine_health(payload: dict) -> dict:
    return evaluate_machine_health(payload)


@router.post("/maintenance-risk")
def maintenance_risk_api(payload: dict) -> dict:
    return maintenance_risk(payload)


@router.get("/maintenance-risk")
def maintenance_risk_history() -> dict:
    df = pd.read_csv(DATA_PATH)
    scored = score_dataframe(df)
    records = scored[["timestamp", "machine_id", "maintenance_risk_score", "risk_level"]].to_dict(orient="records")
    return {"count": len(records), "maintenance_risk": records}


@router.get("/anomalies")
def anomalies() -> dict:
    df = pd.read_csv(DATA_PATH)
    scored = detect_anomalies(df)
    records = scored[["timestamp", "machine_id", "anomaly_label", "anomaly_score"]].to_dict(orient="records")
    return {"count": len(records), "anomalies": records}


@router.post("/root-cause")
def root_cause(payload: dict) -> dict:
    return analyze_root_causes(payload)


@router.get("/root-cause")
def root_cause_history() -> dict:
    df = pd.read_csv(DATA_PATH)
    records = []
    for row in df.to_dict(orient="records"):
        analysis = analyze_root_causes(row)
        records.append(
            {
                "timestamp": row.get("timestamp"),
                "machine_id": row.get("machine_id"),
                "fault_code": row.get("fault_code"),
                "status": analysis["status"],
                "cause_count": analysis["cause_count"],
                "priority": analysis.get("priority", "none"),
                "causes": [cause["cause"] for cause in analysis["causes"]],
            }
        )
    return {"count": len(records), "root_cause_analysis": records}


@router.post("/diagnose")
def diagnose(payload: dict) -> dict:
    return diagnose_against_history(payload)


@router.get("/failure-patterns")
def failure_patterns(machine_id: str | None = None) -> dict:
    patterns = build_failure_patterns(machine_id)
    return {"count": len(patterns), "patterns": patterns}


@router.post("/failure-patterns/learn")
def failure_pattern_learning(payload: dict) -> dict:
    return learn_failure_pattern(payload)


@router.post("/failure-patterns/outcomes")
def failure_pattern_outcome(payload: dict) -> dict:
    return record_learning_outcome(payload)


@router.get("/failure-patterns/summary")
def failure_pattern_summary() -> dict:
    return summarize_learning_outcomes()


@router.get("/diagnose/history")
def diagnosis_history() -> dict:
    history = pd.read_csv(Path("data/maintenance_history.csv"))
    records = history.sort_values("timestamp", ascending=False).head(20).to_dict(orient="records")
    return {"count": len(records), "maintenance_history": records}


@router.get("/part-lifecycle/{machine_id}")
def part_lifecycle(machine_id: str, runtime_hours: float, production_cycles: float, as_of: str | None = None) -> dict:
    parts = active_part_life(
        machine_id=machine_id,
        current_runtime_hours=runtime_hours,
        current_production_cycles=production_cycles,
        as_of=as_of,
    )
    return {"machine_id": machine_id, "count": len(parts), "parts": parts}


@router.post("/part-replacements")
def record_part_replacement(payload: dict) -> dict:
    required = [
        "replacement_id", "machine_id", "part_id", "part_name", "installed_date",
        "runtime_hours_at_install", "production_cycles_at_install",
        "life_runtime_hours", "life_production_cycles", "life_calendar_days",
    ]
    missing = [field for field in required if field not in payload]
    if missing:
        return {"error": "Missing required fields", "fields": missing}

    if payload.get("early_replacement", False):
        validation = validate_early_replacement(payload)
        if validation["status"] == "blocked":
            return validation
        payload = {**payload, **validation}

    history = pd.read_csv(PART_HISTORY_PATH)
    new_row = pd.DataFrame([payload])
    history = pd.concat([history, new_row], ignore_index=True)
    history.to_csv(PART_HISTORY_PATH, index=False)
    return {"status": "recorded", "replacement": payload}


@router.post("/part-replacement/validate")
def validate_part_replacement(payload: dict) -> dict:
    return validate_early_replacement(payload)


@router.get("/spares")
def spares() -> dict:
    df = pd.read_csv(SPARES_PATH)
    analyzed = analyze_inventory(df)
    columns = [
        "spare_id", "part_name", "machine_type", "stock_quantity",
        "minimum_stock", "reorder_point", "monthly_usage", "lead_time_days",
        "unit_cost", "supplier", "critical", "status", "months_of_stock", "action",
    ]
    return {"count": len(analyzed), "spares": analyzed[columns].to_dict(orient="records")}


@router.get("/spares/alerts")
def spare_alerts() -> dict:
    df = pd.read_csv(SPARES_PATH)
    analyzed = analyze_inventory(df)
    alerts = analyzed[analyzed["status"].isin(["out_of_stock", "reorder", "low"])]
    columns = ["spare_id", "part_name", "machine_type", "stock_quantity", "status", "critical", "action"]
    return {"count": len(alerts), "alerts": alerts[columns].to_dict(orient="records")}


@router.post("/spares/recommendation")
def spare_recommendation(payload: dict) -> dict:
    return spare_status(payload)


@router.post("/self-brain/train")
def self_brain_train() -> dict:
    global _SELF_BRAIN
    try:
        _SELF_BRAIN = SelfBrainML()
        metrics = _SELF_BRAIN.train()
        return {"status": "trained", "model": "machine_self_brain", "metrics": metrics}
    except (TypeError, ValueError) as exc:
        _SELF_BRAIN = None
        return {"status": "rejected", "error": str(exc)}


@router.get("/self-brain/status")
def self_brain_status() -> dict:
    if _SELF_BRAIN is None:
        return {"trained": False, "metrics": None}
    return _SELF_BRAIN.status()


@router.post("/self-brain/diagnose")
def self_brain_diagnose(payload: dict) -> dict:
    global _SELF_BRAIN
    readings = payload.get("readings", [])
    if not isinstance(readings, list):
        return {"status": "rejected", "error": "readings must be a list"}
    try:
        quality = assess_telemetry_quality(
            readings,
            reference_time=payload.get("reference_time"),
            stale_after_seconds=int(payload.get("stale_after_seconds", 60)),
        )
        blocking = {"invalid_timestamp", "missing_sensor"}
        blocking_issues = [issue for issue in quality["issues"] if issue["type"] in blocking]
        if blocking_issues:
            return {
                "status": "rejected",
                "reason": "telemetry_quality",
                "quality": quality,
            }
        if _SELF_BRAIN is None:
            _SELF_BRAIN = SelfBrainML()
            _SELF_BRAIN.train()
        result = _SELF_BRAIN.diagnose(readings, machine_id=payload.get("machine_id"))
        result["telemetry_quality"] = quality
        return result
    except (TypeError, ValueError) as exc:
        return {"status": "rejected", "error": str(exc)}
