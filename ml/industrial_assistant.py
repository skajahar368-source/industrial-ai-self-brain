from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.services.health import evaluate_machine_health
from ml.anomaly_detection import score_machine_reading
from ml.failure_pattern_learning import learn_failure_pattern
from ml.part_lifecycle import active_part_life
from ml.predictive_maintenance import maintenance_risk
from ml.root_cause import analyze_root_causes
from ml.spare_management import analyze_inventory

MACHINE_DATA_PATH = Path("data/machine_data.csv")
SPARES_PATH = Path("data/spare_parts.csv")


def _latest_machine_reading(machine_id: str) -> dict[str, Any] | None:
    data = pd.read_csv(MACHINE_DATA_PATH)
    data = data[data["machine_id"].astype(str) == str(machine_id)]
    if data.empty:
        return None
    data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce")
    return data.sort_values("timestamp", ascending=False).iloc[0].to_dict()


def _maintenance_history(machine_id: str) -> pd.DataFrame:
    path = Path("data/maintenance_history.csv")
    history = pd.read_csv(path)
    return history[history["machine_id"].astype(str) == str(machine_id)]


def _spare_for_part(part_name: str | None) -> dict[str, Any] | None:
    if not part_name:
        return None
    spares = analyze_inventory(pd.read_csv(SPARES_PATH))
    matches = spares[spares["part_name"].astype(str).str.lower() == str(part_name).lower()]
    if matches.empty:
        return None
    return matches.iloc[0].to_dict()


def _question_intent(question: str) -> str:
    text = question.lower()
    if any(word in text for word in ("spare", "stock", "inventory", "available")):
        return "spares"
    if any(word in text for word in ("life", "lifecycle", "replacement", "replace", "part")):
        return "lifecycle"
    if any(word in text for word in ("history", "previous", "failure", "failed", "breakdown", "pattern")):
        return "history"
    if any(word in text for word in ("why", "cause", "reason", "diagnos", "problem")):
        return "diagnosis"
    if any(word in text for word in ("risk", "maintenance", "health", "condition", "status", "anomal")):
        return "health"
    return "overview"


def ask_industrial_assistant(payload: dict[str, Any]) -> dict[str, Any]:
    machine_id = str(payload.get("machine_id", "")).strip()
    question = str(payload.get("question", "")).strip()

    if not machine_id:
        return {"status": "blocked", "error": "machine_id is required"}
    if not question:
        return {"status": "blocked", "error": "question is required"}

    reading = _latest_machine_reading(machine_id)
    if reading is None:
        return {
            "status": "not_found",
            "machine_id": machine_id,
            "answer": f"No machine data was found for {machine_id}.",
        }

    health = evaluate_machine_health(reading)
    risk = maintenance_risk(reading)
    baseline = pd.read_csv(MACHINE_DATA_PATH)
    anomaly = score_machine_reading(reading, baseline)
    root_cause = analyze_root_causes(reading)
    causes = [item["cause"] for item in root_cause["causes"]]

    pattern = learn_failure_pattern(
        {
            "machine_id": machine_id,
            "fault_code": reading.get("fault_code"),
            "causes": causes,
        }
    )

    history = _maintenance_history(machine_id)
    intent = _question_intent(question)

    context: dict[str, Any] = {
        "latest_reading": reading,
        "health": health,
        "maintenance_risk": risk,
        "anomaly": anomaly,
        "root_cause": root_cause,
        "failure_pattern": pattern,
        "maintenance_event_count": int(len(history)),
    }

    if intent == "history":
        context["recent_failures"] = history.sort_values("timestamp", ascending=False).head(5).to_dict(
            orient="records"
        )

    if intent == "spares":
        context["spares"] = analyze_inventory(pd.read_csv(SPARES_PATH)).to_dict(orient="records")

    if intent == "lifecycle":
        runtime_hours = payload.get("runtime_hours")
        if runtime_hours is not None:
            context["part_lifecycle"] = active_part_life(
                machine_id=machine_id,
                current_runtime_hours=float(runtime_hours),
                current_production_cycles=float(reading.get("cycle_count", 0)),
                as_of=payload.get("as_of"),
            )
        else:
            context["part_lifecycle"] = {
                "status": "insufficient_input",
                "message": "runtime_hours is required to calculate active part lifecycle.",
            }

    answer_lines = [
        f"Machine {machine_id}: {health['status'].upper()} health.",
        f"Maintenance risk: {risk['risk_level']} ({risk['maintenance_risk_score']}/100).",
    ]

    if risk["factors"]:
        answer_lines.append("Risk factors: " + ", ".join(risk["factors"]) + ".")

    if anomaly.get("anomaly_label") == -1:
        answer_lines.append("Anomaly detector flags the latest reading as unusual.")
    else:
        answer_lines.append("Anomaly detector does not flag the latest reading as unusual.")

    if causes:
        answer_lines.append("Potential causes: " + ", ".join(causes) + ".")
    else:
        answer_lines.append("No current root-cause rule is triggered.")

    if pattern["status"] == "pattern_match":
        matched = pattern["matched_pattern"]
        answer_lines.append(
            f"Historical pattern match: {matched['cause']} with confidence "
            f"{pattern['confidence']:.0%}; previously involved part: "
            f"{matched['part_replaced'] or 'not recorded'}."
        )
    else:
        answer_lines.append("No strong historical failure pattern is established from current evidence.")

    if intent == "spares":
        analyzed = analyze_inventory(pd.read_csv(SPARES_PATH))
        alerts = analyzed[analyzed["status"].isin(["out_of_stock", "reorder", "low"])]
        if alerts.empty:
            answer_lines.append("No spare-stock alerts are currently recorded.")
        else:
            names = ", ".join(alerts["part_name"].astype(str).head(5))
            answer_lines.append(f"Spare-stock alerts: {names}.")

    if intent == "lifecycle":
        lifecycle = context["part_lifecycle"]
        if isinstance(lifecycle, list) and lifecycle:
            due = [p["part_name"] for p in lifecycle if p["status"] in {"replace_now", "replacement_due_soon"}]
            answer_lines.append(
                "Lifecycle attention: " + (", ".join(due) if due else "no active part is currently due soon.")
            )
        elif isinstance(lifecycle, dict):
            answer_lines.append(lifecycle["message"])

    if intent == "history":
        answer_lines.append(f"Recorded maintenance events for this machine: {len(history)}.")

    answer_lines.append(
        "Decision: use this evidence to guide inspection; a human maintenance decision remains final."
    )

    return {
        "status": "ok",
        "machine_id": machine_id,
        "question": question,
        "intent": intent,
        "answer": " ".join(answer_lines),
        "evidence": context,
    }
