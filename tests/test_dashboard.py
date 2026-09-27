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
