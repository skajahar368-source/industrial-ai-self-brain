"""Tests for V3.4 maintenance report trend summaries."""
from ml.maintenance_report_trends import summarize_report_trends


def make_report(report_id, archived_at, health, risk_level, score, fault, anomaly):
    return {
        "status": "ok",
        "machine_id": "M-TREND",
        "report_id": report_id,
        "archived_at_utc": archived_at,
        "summary": {
            "health_status": health,
            "maintenance_risk_level": risk_level,
            "maintenance_risk_score": score,
            "fault_code": fault,
            "anomaly_flagged": anomaly,
            "timestamp": archived_at,
        },
        "evidence_quality": {"status": "available"},
    }


def test_trends_compare_oldest_and_newest_reports_without_diagnosing():
    newest = make_report("r2", "2026-10-21T12:00:00+00:00", "critical", "high", 82, "HIGH_VIBRATION", True)
    oldest = make_report("r1", "2026-10-20T12:00:00+00:00", "warning", "medium", 55, "NORMAL", False)

    result = summarize_report_trends([newest, oldest], "M-TREND")

    assert result["status"] == "ok"
    assert result["report_count"] == 2
    assert result["comparison"]["maintenance_risk_score"]["delta"] == 27.0
    assert result["comparison"]["maintenance_risk_score"]["direction"] == "increased"
    assert result["comparison"]["health_status"]["changed"] is True
    assert result["comparison"]["fault_code"]["to"] == "HIGH_VIBRATION"
    assert result["reports_chronological"][0]["report_id"] == "r1"
    assert result["human_review_required"] is True
    assert result["automatic_diagnosis_performed"] is False
    assert result["model_updated"] is False
    assert result["control_write_performed"] is False
    assert result["plc_write_performed"] is False


def test_trends_report_missing_scores_as_not_comparable():
    newest = make_report("r2", "2026-10-21T12:00:00+00:00", "warning", "medium", None, "X", None)
    oldest = make_report("r1", "2026-10-20T12:00:00+00:00", "warning", "medium", 50, "X", None)

    result = summarize_report_trends([newest, oldest], "M-TREND")

    assert result["comparison"]["maintenance_risk_score"]["delta"] is None
    assert result["comparison"]["maintenance_risk_score"]["direction"] == "not_comparable"
    assert result["comparison"]["anomaly_flagged"]["changed"] is False


def test_trends_require_machine_id_and_return_not_found_when_empty():
    assert summarize_report_trends([], " ")["status"] == "rejected"
    result = summarize_report_trends([], "M-TREND")
    assert result["status"] == "not_found"
    assert result["human_review_required"] is True


def test_trends_api_reads_archived_reports_from_sqlite(monkeypatch, tmp_path):
    from app.api import routes
    from ml.maintenance_report_history import save_report

    db_path = tmp_path / "trend-history.sqlite3"
    monkeypatch.setattr(routes, "MAINTENANCE_REPORT_HISTORY_DB", db_path)

    def archived_report(health, risk_level, score, fault):
        return {
            "status": "ok",
            "machine_id": "M-TREND",
            "summary": {
                "health_status": health,
                "maintenance_risk_level": risk_level,
                "maintenance_risk_score": score,
                "fault_code": fault,
                "anomaly_flagged": None,
                "timestamp": "2026-10-21T12:00:00Z",
            },
            "evidence_quality": {"status": "available"},
            "human_review_required": True,
            "automatic_diagnosis_performed": False,
            "model_updated": False,
            "control_write_performed": False,
            "plc_write_performed": False,
        }

    save_report(archived_report("warning", "medium", 40, "NORMAL"), db_path)
    save_report(archived_report("critical", "high", 75, "HIGH_VIBRATION"), db_path)

    result = routes.maintenance_investigation_report_trends(machine_id="M-TREND", limit=20)

    assert result["status"] == "ok"
    assert result["report_count"] == 2
    assert result["comparison"]["maintenance_risk_score"]["delta"] == 35.0
    assert result["comparison"]["fault_code"]["to"] == "HIGH_VIBRATION"
    assert result["plc_write_performed"] is False


def test_trends_api_requires_machine_id(monkeypatch):
    from app.api import routes

    result = routes.maintenance_investigation_report_trends(machine_id=None, limit=20)

    assert result["status"] == "rejected"
    assert result["error"] == "machine_id is required"
