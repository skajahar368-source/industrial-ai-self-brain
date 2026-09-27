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
