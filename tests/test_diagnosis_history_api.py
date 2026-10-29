from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_diagnosis_history_records_and_filters_by_machine(monkeypatch, tmp_path):
    from ml import diagnosis_history

    monkeypatch.setattr(diagnosis_history, "DEFAULT_DB_PATH", tmp_path / "history.sqlite3")
    first = client.post(
        "/api/self-brain/history",
        json={
            "machine_id": "CR-03",
            "severity": "high",
            "predicted_fault": "vibration",
            "rule_summary": "Vibration exceeded the illustrative threshold",
            "ml_summary": "Model flags possible vibration fault",
            "telemetry_quality": "good",
            "explanation_status": "not_configured",
            "data_provenance": "synthetic test data",
            "raw_readings": [{"temperature_c": 99}],
            "api_key": "must-not-be-stored",
        },
    )
    second = client.post(
        "/api/self-brain/history",
        json={"machine_id": "CR-04", "severity": "low"},
    )

    assert first.status_code == 200
    assert first.json()["status"] == "recorded"
    assert second.json()["status"] == "recorded"

    response = client.get("/api/self-brain/history", params={"machine_id": "CR-03"})
    body = response.json()
    assert body["status"] == "ok"
    assert body["count"] == 1
    saved = body["history"][0]
    assert saved["machine_id"] == "CR-03"
    assert saved["severity"] == "high"
    assert saved["predicted_fault"] == "vibration"
    assert "raw_readings" not in saved
    assert "api_key" not in saved
    assert saved["details"]["write_commands_supported"] is False
    assert saved["details"]["human_decision_required"] is True


def test_diagnosis_history_rejects_invalid_machine_and_limit(monkeypatch, tmp_path):
    from ml import diagnosis_history

    monkeypatch.setattr(diagnosis_history, "DEFAULT_DB_PATH", tmp_path / "history.sqlite3")
    invalid_record = client.post("/api/self-brain/history", json={"machine_id": ""})
    invalid_limit = client.get("/api/self-brain/history", params={"limit": 101})

    assert invalid_record.json()["status"] == "rejected"
    assert invalid_limit.json()["status"] == "rejected"
