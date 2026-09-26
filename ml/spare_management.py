from __future__ import annotations

from typing import Any

import pandas as pd


def spare_status(item: dict[str, Any]) -> dict[str, Any]:
    """Classify spare inventory using transparent reorder logic."""
    stock = float(item.get("stock_quantity", 0))
    minimum = float(item.get("minimum_stock", 0))
    reorder = float(item.get("reorder_point", minimum))
    monthly_usage = float(item.get("monthly_usage", 0))
    critical = bool(item.get("critical", False))

    if stock <= 0:
        status = "out_of_stock"
        action = "Immediate procurement required."
    elif stock <= reorder:
        status = "reorder"
        action = "Create a purchase request."
    elif stock <= minimum:
        status = "low"
        action = "Monitor stock and plan replenishment."
    else:
        status = "healthy"
        action = "No immediate replenishment required."

    if critical and status in {"out_of_stock", "reorder"}:
        action = "Priority procurement required for critical spare."

    months_remaining = None
    if monthly_usage > 0:
        months_remaining = round(stock / monthly_usage, 2)

    return {
        "status": status,
        "action": action,
        "months_of_stock": months_remaining,
        "critical": critical,
    }


def analyze_inventory(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    analysis = result.apply(lambda row: spare_status(row.to_dict()), axis=1)
    result["status"] = [x["status"] for x in analysis]
    result["action"] = [x["action"] for x in analysis]
    result["months_of_stock"] = [x["months_of_stock"] for x in analysis]
    return result
