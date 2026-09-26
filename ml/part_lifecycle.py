from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPLACEMENT_HISTORY_PATH = Path("data/part_replacement_history.csv")
WARNING_UTILIZATION_PERCENT = 75.0
REPLACEMENT_UTILIZATION_PERCENT = 100.0


def load_replacement_history() -> pd.DataFrame:
    return pd.read_csv(REPLACEMENT_HISTORY_PATH)


def _to_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value)).date()


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def calculate_part_life(
    replacement: dict[str, Any],
    current_runtime_hours: float,
    current_production_cycles: float,
    as_of: str | date | None = None,
) -> dict[str, Any]:
    """Calculate life remaining for an installed part using three life meters."""
    installed = _to_date(replacement["installed_date"])
    today = _to_date(as_of) if as_of else date.today()

    calendar_days = max(0, (today - installed).days)
    runtime_used = max(
        0.0,
        _safe_float(current_runtime_hours) - _safe_float(replacement["runtime_hours_at_install"]),
    )
    production_used = max(
        0.0,
        _safe_float(current_production_cycles)
        - _safe_float(replacement["production_cycles_at_install"]),
    )

    runtime_limit = _safe_float(replacement.get("life_runtime_hours"))
    production_limit = _safe_float(replacement.get("life_production_cycles"))
    calendar_limit = _safe_float(replacement.get("life_calendar_days"))

    meters = []
    for name, used, limit, unit in (
        ("runtime", runtime_used, runtime_limit, "hours"),
        ("production", production_used, production_limit, "cycles"),
        ("calendar", float(calendar_days), calendar_limit, "days"),
    ):
        if limit > 0:
            meters.append(
                {
                    "meter": name,
                    "used": round(used, 2),
                    "limit": round(limit, 2),
                    "remaining": round(max(0.0, limit - used), 2),
                    "utilization_percent": round(min(100.0, used / limit * 100), 2),
                    "unit": unit,
                }
            )

    if not meters:
        status = "unknown"
        reason = "No configured life limit is available for this part."
    else:
        due_meters = [
            m for m in meters if m["utilization_percent"] >= REPLACEMENT_UTILIZATION_PERCENT
        ]
        warning_meters = [
            m for m in meters if m["utilization_percent"] >= WARNING_UTILIZATION_PERCENT
        ]

        if due_meters:
            status = "replace_now"
            trigger = max(due_meters, key=lambda m: m["utilization_percent"])
            reason = f"{trigger['meter'].title()} life limit reached."
        elif warning_meters:
            status = "replacement_due_soon"
            trigger = max(warning_meters, key=lambda m: m["utilization_percent"])
            reason = f"{trigger['meter'].title()} life is at {trigger['utilization_percent']:.0f}%."
        else:
            status = "healthy"
            trigger = max(meters, key=lambda m: m["utilization_percent"])
            reason = f"Highest life utilization is {trigger['utilization_percent']:.0f}%."

    return {
        "replacement_id": replacement.get("replacement_id"),
        "machine_id": replacement.get("machine_id"),
        "part_id": replacement.get("part_id"),
        "part_name": replacement.get("part_name"),
        "installed_date": str(installed),
        "calendar_days_used": calendar_days,
        "status": status,
        "reason": reason,
        "meters": meters,
    }


def active_part_life(
    machine_id: str,
    current_runtime_hours: float,
    current_production_cycles: float,
    as_of: str | date | None = None,
) -> list[dict[str, Any]]:
    """Return the latest installation record for every active part on a machine."""
    history = load_replacement_history()
    history["installed_date"] = pd.to_datetime(history["installed_date"], errors="coerce")
    history = history.sort_values("installed_date", ascending=False)

    active = history[history["machine_id"].astype(str) == str(machine_id)]
    if active.empty:
        return []

    active = active.drop_duplicates(subset=["part_id"], keep="first")

    return [
        calculate_part_life(
            row.to_dict(),
            current_runtime_hours=current_runtime_hours,
            current_production_cycles=current_production_cycles,
            as_of=as_of,
        )
        for row in active.to_dict(orient="records")
    ]
