from pathlib import Path

import pandas as pd
from fastapi import APIRouter

from app.services.health import evaluate_machine_health
from ml.anomaly_detection import detect_anomalies
from ml.historical_diagnosis import diagnose_against_history
from ml.failure_pattern_learning import (
    build_failure_patterns,
    learn_failure_pattern,
    record_learning_outcome,
    summarize_learning_outcomes,
)
from ml.part_lifecycle import active_part_life
from ml.predictive_maintenance import maintenance_risk, score_dataframe
from ml.replacement_workflow import validate_early_replacement
from ml.root_cause import analyze_root_causes
from ml.spare_management import analyze_inventory, spare_status

router = APIRouter(prefix="/api")
DATA_PATH = Path("data/machine_data.csv")
SPARES_PATH = Path("data/spare_parts.csv")
PART_HISTORY_PATH = Path("data/part_replacement_history.csv")


@router.get("/health")
def api_health() -> dict:
    return {"status": "healthy"}


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
