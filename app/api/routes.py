from pathlib import Path

import pandas as pd
from fastapi import APIRouter

from app.services.health import evaluate_machine_health
from ml.anomaly_detection import detect_anomalies
from ml.predictive_maintenance import maintenance_risk, score_dataframe
from ml.spare_management import analyze_inventory, spare_status

router = APIRouter(prefix="/api")
DATA_PATH = Path("data/machine_data.csv")
SPARES_PATH = Path("data/spare_parts.csv")


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
