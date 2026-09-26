from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

HISTORY_PATH = Path("data/maintenance_history.csv")
OUTCOMES_PATH = Path("data/failure_learning_outcomes.csv")


def load_maintenance_history() -> pd.DataFrame:
    return pd.read_csv(HISTORY_PATH)


def load_learning_outcomes() -> pd.DataFrame:
    if not OUTCOMES_PATH.exists():
        return pd.DataFrame(
            columns=[
                "event_timestamp",
                "machine_id",
                "fault_code",
                "cause",
                "part_replaced",
                "repair_successful",
                "verification_result",
            ]
        )
    return pd.read_csv(OUTCOMES_PATH)


def _norm(value: Any) -> str:
    return str(value).strip().lower()


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _norm(value) in {"true", "1", "yes", "y", "successful", "success"}


def build_failure_patterns(machine_id: str | None = None) -> list[dict[str, Any]]:
    history = load_maintenance_history().copy()
    if history.empty:
        return []

    if machine_id:
        history = history[history["machine_id"].astype(str) == str(machine_id)]

    if history.empty:
        return []

    history["cause_key"] = history["cause"].map(_norm)
    history["fault_key"] = history["fault_code"].map(_norm)
    history["part_key"] = history["part_replaced"].fillna("").map(_norm)

    grouped = (
        history.groupby(["machine_id", "cause_key", "fault_key", "part_key"], dropna=False)
        .agg(
            occurrences=("cause", "size"),
            latest_event=("timestamp", "max"),
            total_downtime_minutes=("downtime_minutes", "sum"),
            average_downtime_minutes=("downtime_minutes", "mean"),
        )
        .reset_index()
    )

    patterns: list[dict[str, Any]] = []
    for row in grouped.to_dict(orient="records"):
        patterns.append(
            {
                "machine_id": row["machine_id"],
                "cause": row["cause_key"],
                "fault_code": row["fault_key"],
                "part_replaced": row["part_key"] or None,
                "occurrences": int(row["occurrences"]),
                "latest_event": row["latest_event"],
                "total_downtime_minutes": float(row["total_downtime_minutes"]),
                "average_downtime_minutes": round(float(row["average_downtime_minutes"]), 2),
            }
        )
    return sorted(patterns, key=lambda x: (x["occurrences"], x["latest_event"]), reverse=True)


def _match_score(
    current: dict[str, Any],
    pattern: dict[str, Any],
) -> tuple[float, list[str]]:
    current_machine = str(current.get("machine_id", ""))
    current_fault = _norm(current.get("fault_code", ""))
    current_causes = {_norm(x) for x in current.get("causes", [])}

    score = 0.0
    evidence: list[str] = []

    if current_machine and current_machine == str(pattern["machine_id"]):
        score += 0.25
        evidence.append("same_machine")

    if pattern["cause"] in current_causes:
        score += 0.40
        evidence.append("same_cause")

    if current_fault and pattern["fault_code"] and current_fault == pattern["fault_code"]:
        score += 0.25
        evidence.append("same_fault_code")

    if int(pattern["occurrences"]) >= 2:
        score += min(0.10, 0.05 * (int(pattern["occurrences"]) - 1))
        evidence.append("repeated_pattern")

    return min(score, 1.0), evidence


def learn_failure_pattern(payload: dict[str, Any]) -> dict[str, Any]:
    patterns = build_failure_patterns(payload.get("machine_id"))
    current_causes = payload.get("causes") or []

    if not current_causes:
        return {
            "status": "insufficient_evidence",
            "confidence": 0.0,
            "matched_pattern": None,
            "evidence": [],
            "recommendation": "Collect machine symptoms and root-cause evidence before using historical patterns.",
        }

    ranked = []
    for pattern in patterns:
        score, evidence = _match_score(payload, pattern)
        if score > 0:
            ranked.append({**pattern, "confidence": round(score, 2), "evidence": evidence})

    ranked.sort(key=lambda x: (x["confidence"], x["occurrences"]), reverse=True)

    if not ranked or ranked[0]["confidence"] < 0.60:
        return {
            "status": "no_strong_pattern",
            "confidence": ranked[0]["confidence"] if ranked else 0.0,
            "matched_pattern": ranked[0] if ranked else None,
            "evidence": ranked[0]["evidence"] if ranked else [],
            "recommendation": "Inspect the machine and collect more evidence; do not directly replace a part.",
        }

    best = ranked[0]
    return {
        "status": "pattern_match",
        "confidence": best["confidence"],
        "matched_pattern": best,
        "evidence": best["evidence"],
        "recommendation": (
            f"Historical pattern suggests investigating '{best['cause']}'. "
            f"Previously involved part: {best['part_replaced'] or 'none recorded'}. "
            "Verify the cause before replacement."
        ),
        "alternative_patterns": ranked[1:4],
    }


def record_learning_outcome(payload: dict[str, Any]) -> dict[str, Any]:
    required = [
        "event_timestamp",
        "machine_id",
        "fault_code",
        "cause",
        "part_replaced",
        "repair_successful",
        "verification_result",
    ]
    missing = [field for field in required if field not in payload]
    if missing:
        return {"status": "blocked", "fields": missing}

    verification = str(payload.get("verification_result", "")).strip()
    if not verification:
        return {"status": "blocked", "error": "verification_result is required"}

    row = {field: payload[field] for field in required}
    history = load_learning_outcomes()
    history = pd.concat([history, pd.DataFrame([row])], ignore_index=True)
    history.to_csv(OUTCOMES_PATH, index=False)

    return {
        "status": "recorded",
        "outcome": row,
        "message": "Repair outcome recorded as new learning evidence.",
    }


def summarize_learning_outcomes() -> dict[str, Any]:
    outcomes = load_learning_outcomes()
    if outcomes.empty:
        return {"count": 0, "successful_repairs": 0, "success_rate": None}

    successful = outcomes["repair_successful"].map(_bool)
    return {
        "count": int(len(outcomes)),
        "successful_repairs": int(successful.sum()),
        "success_rate": round(float(successful.mean()), 3),
    }
