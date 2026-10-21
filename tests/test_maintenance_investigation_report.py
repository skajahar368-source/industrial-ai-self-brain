"""V3.0 tests for structured maintenance investigation reports."""

from app.api import routes


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
    assert report["report_version"] == "3.0"
    assert report["summary"]["fault_code"] == "HIGH_VIBRATION"
    assert report["summary"]["maintenance_risk_level"] == "high"
    assert report["summary"]["anomaly_flagged"] is True
    assert report["evidence_sources"]["rule_based_findings"]["findings"][0]["cause"] == "Excessive vibration"
    assert report["evidence_sources"]["verified_maintenance_history"]["matching_verified_cases"] == 2
    assert report["recommended_checks"][0]["source"] == "deterministic_root_cause_rule"
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
    from ml.maintenance_investigation_report import build_maintenance_investigation_report

    report = build_maintenance_investigation_report({
        "status": "ok",
        "machine_id": "M-REPORT",
        "evidence": [],
    })

    assert report["status"] == "blocked"
    assert "evidence must be an object" in report["error"]
