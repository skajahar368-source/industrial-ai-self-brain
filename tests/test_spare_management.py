import pandas as pd

from ml.spare_management import analyze_inventory, spare_status


def test_out_of_stock_is_immediate():
    result = spare_status({"stock_quantity": 0, "minimum_stock": 3, "reorder_point": 4, "monthly_usage": 1, "critical": True})
    assert result["status"] == "out_of_stock"
    assert "Immediate procurement" in result["action"]


def test_low_stock_triggers_reorder():
    result = spare_status({"stock_quantity": 4, "minimum_stock": 5, "reorder_point": 6, "monthly_usage": 2, "critical": False})
    assert result["status"] == "reorder"


def test_healthy_inventory():
    df = pd.DataFrame([
        {"stock_quantity": 20, "minimum_stock": 5, "reorder_point": 7, "monthly_usage": 2, "critical": False}
    ])
    result = analyze_inventory(df)
    assert result.iloc[0]["status"] == "healthy"
    assert result.iloc[0]["months_of_stock"] == 10.0
