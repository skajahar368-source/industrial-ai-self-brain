from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_dashboard_is_available():
    response=client.get("/dashboard")
    assert response.status_code==200
    assert "Industrial AI" in response.text
    assert "Self-Brain" in response.text
