from app.api.routes import simulator_demo


def test_simulator_demo_runs_full_read_only_pipeline():
    result = simulator_demo({
        "machine_id": "M-DEMO-TEST",
        "scenario": "vibration",
        "count": 24,
    })

    assert result["status"] == "ok"
    assert result["demo"]["samples"] == 24
    assert result["plc"]["scenario"] == "vibration"
    assert result["brain"]["status"] == "ok"
    assert result["root_cause"]["cause_count"] >= 1
    assert result["control_write_performed"] is False
