from ml.machine_state import MachineState, MachineStateEngine


def test_machine_lifecycle():
    engine = MachineStateEngine()
    assert engine.snapshot()["state"] == "OFFLINE"
    assert engine.start() == MachineState.STARTING
    assert engine.complete_startup() == MachineState.RUNNING
    engine.record_cycle()
    assert engine.snapshot()["cycle_count"] == 1


def test_health_drives_warning_degraded_and_fault():
    engine = MachineStateEngine(state=MachineState.RUNNING)
    assert engine.evaluate(health_score=70) == MachineState.WARNING
    assert engine.evaluate(health_score=50) == MachineState.DEGRADED
    assert engine.evaluate(health_score=20, alarm_active=True) == MachineState.FAULT


def test_maintenance_state_is_protected():
    engine = MachineStateEngine(state=MachineState.RUNNING)
    engine.enter_maintenance()
    assert engine.evaluate(health_score=100, alarm_active=False) == MachineState.MAINTENANCE
    assert engine.complete_maintenance() == MachineState.OFFLINE
