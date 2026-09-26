from ml.part_lifecycle import calculate_part_life


def replacement(**overrides):
    data = {
        "replacement_id": "PR-TEST",
        "machine_id": "M-001",
        "part_id": "SP-001",
        "part_name": "Bearing 6204",
        "installed_date": "2026-01-01",
        "runtime_hours_at_install": 1000,
        "production_cycles_at_install": 10000,
        "life_runtime_hours": 3000,
        "life_production_cycles": 50000,
        "life_calendar_days": 365,
    }
    data.update(overrides)
    return data


def test_part_is_healthy_when_usage_is_low():
    result = calculate_part_life(replacement(), 1500, 20000, "2026-03-01")
    assert result["status"] == "healthy"


def test_part_warns_before_end_of_life():
    result = calculate_part_life(replacement(), 3300, 30000, "2026-06-01")
    assert result["status"] == "replacement_due_soon"


def test_part_is_due_when_runtime_limit_is_reached():
    result = calculate_part_life(replacement(), 4000, 20000, "2026-03-01")
    assert result["status"] == "replace_now"
    assert "Runtime" in result["reason"]


def test_production_limit_can_trigger_replacement():
    result = calculate_part_life(replacement(), 1500, 60000, "2026-03-01")
    assert result["status"] == "replace_now"
    assert "Production" in result["reason"]


def test_calendar_limit_can_trigger_replacement():
    result = calculate_part_life(replacement(), 1500, 20000, "2027-01-01")
    assert result["status"] == "replace_now"
    assert "Calendar" in result["reason"]
