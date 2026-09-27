from fastapi.testclient import TestClient

from app.main import app
from ml.validation_center import run_validation_suite

client = TestClient(app)


def test_validation_suite_passes_without_writing_telemetry():
    result = run_validation_suite()
    assert result["status"] == "passed"
    assert result["total_cases"] == 8
    assert result["failed"] == 0


def test_validation_suite_covers_combined_failure_and_invalid_inputs():
    result = client.get("/api/validation/run")
    assert result.status_code == 200

    cases = {case["name"]: case for case in result.json()["cases"]}

    assert cases["combined_failure"]["actual_health"] == "critical"
    assert cases["negative_temperature_rejected"]["status"] == "passed"
    assert cases["invalid_timestamp_rejected"]["status"] == "passed"
    assert cases["missing_required_sensor_rejected"]["status"] == "passed"
