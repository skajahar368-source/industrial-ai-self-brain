from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_dashboard_is_available():
    response=client.get("/dashboard")
    assert response.status_code==200
    assert "Industrial AI" in response.text
    assert "Self-Brain" in response.text

def test_dashboard_overview_returns_machine_snapshot():
    response = client.get("/api/dashboard/overview?machine_id=M-001")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["machine_id"] == "M-001"
    assert "latest_telemetry" in body
    assert "health" in body
    assert "maintenance_risk" in body
    assert "anomaly" in body
    assert "root_cause" in body
    assert "spare_alerts" in body

def test_simulation_endpoint_generates_reading():
    response = client.post(
        "/api/telemetry/simulate",
        json={"machine_id": "M-SIM-001", "step": 10, "scenario": "failure"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["reading"]["fault_code"] == "HIGH_TEMP_PRESSURE"


def test_simulation_batch_endpoint_generates_multiple_readings():
    response = client.post(
        "/api/telemetry/simulate-batch",
        json={"machine_id": "M-SIM-002", "start_step": 0, "count": 3, "scenario": "warning"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] == 3

def test_dashboard_overview_includes_trend_analysis():
    response = client.get("/api/dashboard/overview?machine_id=M-001")
    assert response.status_code == 200
    body = response.json()
    assert "trend_analysis" in body
    assert body["trend_analysis"]["status"] in {"ok", "insufficient_data"}

def test_dashboard_overview_includes_degradation_timeline():
    response = client.get("/api/dashboard/overview?machine_id=M-001")
    assert response.status_code == 200
    body = response.json()
    assert "degradation_timeline" in body
    assert body["degradation_timeline"]["status"] in {"ok", "insufficient_data"}

def test_failure_model_train_endpoint():
    response = client.post("/api/failure-model/train")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "trained"
    assert "metrics" in body
    assert body["training_samples"] >= 1


def test_failure_prediction_endpoint_requires_training_or_predicts():
    client.post("/api/failure-model/train")
    response = client.post(
        "/api/failure-prediction",
        json={
            "temperature_c": 82,
            "pressure_bar": 101,
            "vibration_mm_s": 8.4,
            "cycle_count": 1450,
            "downtime_minutes": 35,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "predicted"
    assert 0 <= body["failure_probability"] <= 1
    assert body["human_decision_required"] is True


def test_virtual_plc_snapshot_is_simulated_and_read_only():
    response = client.get(
        "/api/virtual-plc/snapshot",
        params={"machine_id": "M-PLC-API", "step": 10, "scenario": "failure"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["machine_id"] == "M-PLC-API"
    assert body["machine_state"] == "FAULT"
    assert body["alarm_state"] == "ACTIVE"
    assert body["read_only"] is True
    assert body["real_plc_connected"] is False
    assert body["write_commands_supported"] is False


def test_virtual_plc_snapshot_rejects_unknown_scenario():
    response = client.get(
        "/api/virtual-plc/snapshot",
        params={"scenario": "unknown"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"



def test_virtual_plc_diagnose_is_rule_based_and_read_only():
    response = client.get(
        "/api/virtual-plc/diagnose",
        params={"machine_id": "M-DIAG-01", "step": 10, "scenario": "failure"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["analysis_is_ai_generated"] is False
    assert body["read_only"] is True
    assert body["real_plc_connected"] is False
    assert body["write_commands_supported"] is False
    assert body["diagnosis"]["analysis_type"] == "deterministic_rules"
    assert body["diagnosis"]["severity"] == "high"
    assert body["diagnosis"]["human_decision_required"] is True


def test_virtual_plc_diagnose_rejects_unknown_scenario():
    response = client.get("/api/virtual-plc/diagnose", params={"scenario": "unknown"})
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
