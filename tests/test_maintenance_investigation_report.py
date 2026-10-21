"""V3.1 tests for evidence quality in structured maintenance reports."""

from app.api import routes
from ml.maintenance_investigation_report import build_maintenance_investigation_report


def assistant_result():
    return {
        "status": "ok",
        "machine_id": "M-REPORT",
        "question": "Investigate the machine condition",
        "evidence": {
            "latest_reading": {
                "machine_id": "M-REPORT",
                "timestamp": "2026-10-21T10:00:00Z",
                "fault_code": "HIGH_VIBRATION",
                "vibration_mm_s": 8.2,
            },
            "health": {"status": "warning"},
            "maintenance_risk": {"risk_level": "high", "maintenance_risk_score": 82},
            "anomaly": {"anomaly_label": -1},
            "root_cause": {
                "status": "causes_detected",
                "causes": [{
                    "cause": "Excessive vibration",
                    "evidence": "Vibration exceeds the configured threshold.",
                    "recommended_action": "Inspect bearings and alignment.",
                }],
            },
            "verified_maintenance_context": {
                "evidence_label": "human_verified_historical_context",
                "evidence_count": 1,
                "matching_verified_cases": 2,
                "evidence": [{
                    "cause": "bearing wear",
                    "verified_cases": 2,
                    "successful_repairs": 2,
                    "evidence_status": "human_verified",
                    "repair_actions": ["replace bearing"],
                }],
                "interpretation": "Past repairs are historical context, not proof of current cause.",
                "automatic_diagnosis_performed": False,
                "model_updated": False,
                "control_write_performed": False,
            },
        },
    }


def test_report_groups_sources_and_keeps_safety_boundaries(monkeypatch):
    monkeypatch.setattr(routes, "ask_industrial_assistant", lambda payload: assistant_result())

    report = routes.maintenance_investigation_report({
        "machine_id": "M-REPORT",
        "question": "Investigate the machine condition",
    })

    assert report["status"] == "ok"
    assert report["report_version"] == "3.1"
    assert report["summary"]["fault_code"] == "HIGH_VIBRATION"
    assert report["summary"]["maintenance_risk_level"] == "high"
    assert report["summary"]["anomaly_flagged"] is True
    assert report["evidence_sources"]["rule_based_findings"]["findings"][0]["cause"] == "Excessive vibration"
    assert report["evidence_sources"]["verified_maintenance_history"]["matching_verified_cases"] == 2
    assert report["recommended_checks"][0]["source"] == "deterministic_root_cause_rule"
    assert report["evidence_quality"]["status"] == "available"
    assert report["evidence_quality"]["numeric_measurement_count"] == 1
    assert report["evidence_quality"]["recommended_check_count"] == 1
    assert report["human_review_required"] is True
    assert report["automatic_diagnosis_performed"] is False
    assert report["model_updated"] is False
    assert report["control_write_performed"] is False
    assert report["plc_write_performed"] is False


def test_report_propagates_assistant_blocked_or_not_found_status(monkeypatch):
    monkeypatch.setattr(
        routes,
        "ask_industrial_assistant",
        lambda payload: {"status": "blocked", "error": "machine_id is required"},
    )

    report = routes.maintenance_investigation_report({"question": "Investigate"})

    assert report["status"] == "blocked"
    assert report["error"] == "machine_id is required"


def test_report_rejects_malformed_evidence():
    report = build_maintenance_investigation_report({
        "status": "ok",
        "machine_id": "M-REPORT",
        "evidence": [],
    })

    assert report["status"] == "blocked"
    assert "evidence must be an object" in report["error"]


def test_missing_context_is_reported_and_unknown_anomaly_is_not_false():
    result = assistant_result()
    evidence = result["evidence"]
    evidence["latest_reading"] = {"machine_id": "M-REPORT"}
    evidence["anomaly"] = {}

    report = build_maintenance_investigation_report(result)

    assert report["status"] == "ok"
    assert report["evidence_quality"]["status"] == "partial"
    assert report["evidence_quality"]["missing_context"] == [
        "reading_timestamp",
        "fault_code",
        "numeric_sensor_measurements",
    ]
    assert report["summary"]["anomaly_flagged"] is None


def test_non_dictionary_assistant_result_is_blocked():
    report = build_maintenance_investigation_report(None)
    assert report["status"] == "blocked"
    assert report["error"] == "Assistant result must be an object."


def test_download_endpoint_returns_json_attachment(monkeypatch, tmp_path):
    import json

    monkeypatch.setattr(routes, "MAINTENANCE_REPORT_HISTORY_DB", tmp_path / "reports.sqlite3")
    monkeypatch.setattr(routes, "ask_industrial_assistant", lambda payload: assistant_result())

    response = routes.download_maintenance_investigation_report({
        "machine_id": "M-REPORT",
        "question": "Investigate the machine condition",
    })

    assert response.status_code == 200
    assert response.media_type == "application/json"
    assert response.headers["content-disposition"] == (
        'attachment; filename="self-brain-maintenance-report-M-REPORT.json"'
    )
    downloaded = json.loads(response.body)
    assert downloaded["report_version"] == "3.1"
    assert downloaded["human_review_required"] is True
    assert downloaded["plc_write_performed"] is False


def test_download_endpoint_does_not_attach_blocked_report(monkeypatch, tmp_path):
    monkeypatch.setattr(routes, "MAINTENANCE_REPORT_HISTORY_DB", tmp_path / "reports.sqlite3")
    monkeypatch.setattr(
        routes,
        "ask_industrial_assistant",
        lambda payload: {"status": "blocked", "error": "machine_id is required"},
    )

    response = routes.download_maintenance_investigation_report({"question": "Investigate"})

    assert response.status_code == 400
    assert "content-disposition" not in response.headers



def test_successful_report_is_archived_and_can_be_listed_and_retrieved(monkeypatch, tmp_path):
    from ml.maintenance_report_history import get_report, list_reports

    db_path = tmp_path / "reports.sqlite3"
    monkeypatch.setattr(routes, "MAINTENANCE_REPORT_HISTORY_DB", db_path)
    monkeypatch.setattr(routes, "ask_industrial_assistant", lambda payload: assistant_result())

    created = routes.maintenance_investigation_report({
        "machine_id": "M-REPORT",
        "question": "Investigate the machine condition",
    })

    assert created["status"] == "ok"
    assert created["history_saved"] is True
    assert created["report_id"]
    assert created["archived_at_utc"]

    listing = list_reports(db_path, machine_id="M-REPORT")
    assert listing["status"] == "ok"
    assert listing["count"] == 1
    assert listing["reports"][0]["report_id"] == created["report_id"]
    assert listing["reports"][0]["fault_code"] == "HIGH_VIBRATION"

    stored = get_report(created["report_id"], db_path)
    assert stored["report_id"] == created["report_id"]
    assert stored["summary"]["fault_code"] == "HIGH_VIBRATION"
    assert stored["plc_write_performed"] is False


def test_blocked_report_is_not_archived(monkeypatch, tmp_path):
    from ml.maintenance_report_history import list_reports

    db_path = tmp_path / "reports.sqlite3"
    monkeypatch.setattr(routes, "MAINTENANCE_REPORT_HISTORY_DB", db_path)
    monkeypatch.setattr(
        routes,
        "ask_industrial_assistant",
        lambda payload: {"status": "blocked", "error": "machine_id is required"},
    )

    result = routes.maintenance_investigation_report({"question": "Investigate"})

    assert result["status"] == "blocked"
    assert list_reports(db_path)["count"] == 0


def test_history_rejects_invalid_limit_and_reports_unknown_id(tmp_path):
    from ml.maintenance_report_history import get_report, list_reports

    db_path = tmp_path / "reports.sqlite3"
    assert list_reports(db_path, limit=101)["status"] == "rejected"
    missing = get_report("missing-report-id", db_path)
    assert missing["status"] == "not_found"
