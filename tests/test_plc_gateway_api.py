from app.api.routes import gateway_scan, plc_configure, plc_status


def test_gateway_scan_connects_plc_to_telemetry_and_health():
    result = gateway_scan({"machine_id": "M-GATE-API", "scenario": "normal"})

    assert result["status"] == "ok"
    assert result["pipeline"].startswith("PLC -> Gateway")
    assert result["plc"]["machine_id"] == "M-GATE-API"
    assert result["telemetry"]["source"] == "virtual-plc-gateway"
    assert result["health"]["status"] in {"normal", "warning", "critical"}
    assert result["control_write_performed"] is False
    assert result["brain"]["status"] == "warming_up"


def test_plc_configuration_and_status_are_read_only():
    configured = plc_configure({
        "machine_id": "M-CONFIG-API",
        "scenario": "failure",
        "mode": "AUTO",
    })
    status = plc_status("M-CONFIG-API")

    assert configured["status"] == "configured"
    assert status["plc"]["scenario"] == "failure"
    assert status["plc"]["mode"] == "AUTO"
    assert status["plc"]["read_only_to_self_brain"] is True
