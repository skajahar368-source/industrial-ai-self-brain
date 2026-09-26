from pathlib import Path

import pandas as pd
from fastapi import APIRouter

from app.services.health import evaluate_machine_health
from ml.anomaly_detection import detect_anomalies
from ml.predictive_maintenance import maintenance_risk, score_dataframe

router = APIRouter(prefix="/api")
DATA_PATH = Path("data/machine_data.csv")


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
    records = scored[
        ["timestamp", "machine_id", "anomaly_label", "anomaly_score"]
    ].to_dict(orient="records")
    return {"count": len(records), "anomalies": records}
