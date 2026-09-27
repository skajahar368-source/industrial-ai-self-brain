from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

MACHINE = "M-VALIDATION"


def test_self_brain_end_to_end_validation():
    normal = client.post(
        "/api/telemetry/simulate",
        json={"machine_id": MACHINE, "step": 0, "scenario": "normal"},
    )
    warning = client.post(
        "/api/telemetry/simulate",
        json={"machine_id": MACHINE, "step": 10, "scenario": "warning"},
    )
    failure = client.post(
        "/api/telemetry/simulate",
        json={"machine_id": MACHINE, "step": 10, "scenario": "failure"},
    )

    assert normal.json()["status"] == "accepted"
    assert warning.json()["status"] == "accepted"
    assert failure.json()["status"] == "accepted"

    overview = client.get(f"/api/dashboard/overview?machine_id={MACHINE}")
    assert overview.status_code == 200
    body = overview.json()

    assert body["status"] == "ok"
    assert body["machine_id"] == MACHINE
    assert body["health"]["status"] == "critical"
    assert body["maintenance_risk"]["risk_level"] == "high"
    assert body["trend_analysis"]["trend"] == "deteriorating"
    assert body["degradation_timeline"]["direction"] in {
        "deteriorating",
        "rapid_deterioration",
    }

    training = client.post("/api/failure-model/train")
    assert training.status_code == 200
    assert training.json()["status"] == "trained"
    assert training.json()["training_samples"] >= 1

    prediction = client.post(
        "/api/failure-prediction",
        json=failure.json()["reading"],
    )
    assert prediction.status_code == 200
    prediction_body = prediction.json()
    assert prediction_body["status"] == "predicted"
    assert 0 <= prediction_body["failure_probability"] <= 1
    assert prediction_body["human_decision_required"] is True
