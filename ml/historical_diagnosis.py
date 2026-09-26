from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ml.root_cause import analyze_root_causes

HISTORY_PATH = Path("data/maintenance_history.csv")
SPARES_PATH = Path("data/spare_parts.csv")


def load_history() -> pd.DataFrame:
    return pd.read_csv(HISTORY_PATH)


def _normalize(value: Any) -> str:
    return str(value).strip().lower()


def diagnose_against_history(payload: dict[str, Any]) -> dict[str, Any]:
    history = load_history()
    machine_id = payload.get("machine_id")
    if machine_id:
        history = history[history["machine_id"].astype(str) == str(machine_id)]

    history["timestamp"] = pd.to_datetime(history["timestamp"], errors="coerce")
    history = history.sort_values("timestamp", ascending=False)

    current = analyze_root_causes(payload)
    current_causes = {_normalize(x["cause"]) for x in current["causes"]}

    last_event = history.iloc[0].to_dict() if not history.empty else None
    matching_events = []

    if not history.empty and current_causes:
        for row in history.to_dict(orient="records"):
            if _normalize(row["cause"]) in current_causes:
                matching_events.append(row)

    recommendation = {
        "decision": "inspect_and_collect_more_evidence",
        "part": None,
        "reason": "No sufficiently strong historical match for a direct replacement recommendation.",
    }

    if matching_events:
        latest_match = matching_events[0]
        part = str(latest_match.get("part_replaced", "")).strip()
        if part:
            recommendation = {
                "decision": "inspect_then_consider_replacement",
                "part": part,
                "reason": (
                    f"The current symptoms match the historical cause '{latest_match['cause']}', "
                    f"and that event previously involved {part}."
                ),
            }

    return {
        "machine_id": machine_id,
        "current_causes": sorted(current_causes),
        "last_stoppage": last_event,
        "matching_historical_events": matching_events[:5],
        "historical_match": bool(matching_events),
        "recommendation": recommendation,
    }
