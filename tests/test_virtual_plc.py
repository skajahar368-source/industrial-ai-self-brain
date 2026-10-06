from ml.plc_gateway import plc_snapshot_to_telemetry
from ml.virtual_plc import VirtualPLC


def test_virtual_plc_exposes_machine_tags_without_control_writes():
    plc = VirtualPLC("M-TEST", "normal")
    first = plc.scan()
    second = plc.scan()

    assert first["machine_id"] == "M-TEST"
    assert second["heartbeat"] == 2
    assert second["cycle_count"] > first["cycle_count"]
    assert second["read_only_to_self_brain"] is True
    assert "control_command" not in second


def test_virtual_plc_failure_scenario_sets_alarm():
    plc = VirtualPLC("M-FAIL", "combined")
    snapshot = plc.scan()

    assert snapshot["state"] == "FAULT"
    assert snapshot["alarm_active"] is True
    assert snapshot["fault_code"] != "NONE"


def test_gateway_maps_plc_registers_to_normalized_telemetry():
    plc = VirtualPLC("M-GATE", "thermal")
    snapshot = plc.scan()
    telemetry = plc_snapshot_to_telemetry(snapshot)

    assert telemetry["machine_id"] == "M-GATE"
    assert telemetry["source"] == "virtual-plc-gateway"
    assert telemetry["temperature_c"] == snapshot["motor_temperature_c"]
    assert telemetry["sequence_id"] == "PLC-M-GATE-1"


def test_virtual_plc_supports_specific_fault_modes():
    for scenario in ("thermal", "pressure", "vibration", "combined"):
        plc = VirtualPLC(f"M-{scenario}", scenario)
        snapshot = plc.scan()
        assert snapshot["scenario"] == scenario
        assert snapshot["fault_code"] != "NONE"
