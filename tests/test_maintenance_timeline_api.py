"""API tests for the V3.5 machine maintenance timeline."""
from app.api import routes
from ml.maintenance_report_history import save_report
from ml.verified_maintenance_learning import VerifiedMaintenanceLearning


def test_timeline_api_combines_sqlite_reports_and_verified_repairs(monkeypatch, tmp_path):
    report_db = tmp_path / "reports.sqlite3"
    maintenance_db = tmp_path / "maintenance.sqlite3"
    monkeypatch.setattr(routes, "MAINTENANCE_REPORT_HISTORY_DB", report_db)
    monkeypatch.setattr(routes, "VERIFIED_MAINTENANCE_DB", maintenance_db)

    save_report({
        "status": "ok",
        "machine_id": "M-API",
        "summary": {
            "timestamp": "2026-11-01T09:00:00Z",
            "fault_code": "HIGH_VIBRATION",
            "health_status": "warning",
            "maintenance_risk_level": "medium",
            "maintenance_risk_score": 60,
            "anomaly_flagged": True,
        },
        "evidence_quality": {"status": "available"},
    }, report_db)

    store = VerifiedMaintenanceLearning(maintenance_db)
    recorded = store.record({
        "event_timestamp": "2026-11-01T10:00:00Z",
        "machine_id": "M-API",
        "fault_code": "HIGH_VIBRATION",
        "cause": "bearing wear",
        "repair_action": "replace bearing",
        "repair_successful": True,
        "verified": True,
        "verified_by": "maintenance-engineer",
        "verification_method": "post-repair vibration measurement",
        "verification_result": "vibration returned to baseline",
    })
    assert recorded["status"] == "recorded"
    store.close()

    result = routes.maintenance_timeline(machine_id="M-API", limit=10)

    assert result["status"] == "ok"
    assert result["total_events"] == 2
    assert [event["event_type"] for event in result["events"]] == [
        "verified_maintenance", "investigation_report"
    ]
    assert result["plc_write_performed"] is False


def test_timeline_api_requires_machine_id_and_valid_limit():
    assert routes.maintenance_timeline(machine_id=None)["status"] == "rejected"
    assert routes.maintenance_timeline(machine_id="M-API", limit=101)["status"] == "rejected"
