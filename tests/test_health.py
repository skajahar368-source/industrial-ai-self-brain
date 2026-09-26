from app.services.health import evaluate_machine_health

def test_normal_machine():
    result = evaluate_machine_health({'temperature_c': 55, 'pressure_bar': 55, 'vibration_mm_s': 2})
    assert result['status'] == 'normal'

def test_critical_machine():
    result = evaluate_machine_health({'temperature_c': 85, 'pressure_bar': 55, 'vibration_mm_s': 2})
    assert result['status'] == 'critical'

def test_pressure_warning():
    result = evaluate_machine_health({'temperature_c': 55, 'pressure_bar': 20, 'vibration_mm_s': 2})
    assert result['status'] == 'warning'
