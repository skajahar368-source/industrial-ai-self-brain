"""PLC-to-Self-Brain data gateway.

The gateway is the boundary between a PLC adapter and the normalized telemetry
API. The first adapter is VirtualPLC; future adapters can map OPC UA, Modbus,
MQTT, or a manufacturer gateway into the same normalized shape.
"""
from __future__ import annotations

from typing import Any

from ml.telemetry_ingestion import ingest_reading
from ml.virtual_plc import VirtualPLC


def plc_snapshot_to_telemetry(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Map PLC tags into the repository's normalized telemetry contract."""
    required = (
        "machine_id",
        "motor_temperature_c",
        "pressure_bar",
        "vibration_mm_s",
        "cycle_count",
        "downtime_minutes",
        "fault_code",
    )
    missing = [field for field in required if field not in snapshot]
    if missing:
        raise ValueError(f"Missing PLC tags: {missing}")

    from datetime import datetime, timezone

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "machine_id": str(snapshot["machine_id"]),
        "temperature_c": float(snapshot["motor_temperature_c"]),
        "pressure_bar": float(snapshot["pressure_bar"]),
        "vibration_mm_s": float(snapshot["vibration_mm_s"]),
        "cycle_count": float(snapshot["cycle_count"]),
        "downtime_minutes": float(snapshot["downtime_minutes"]),
        "fault_code": str(snapshot["fault_code"]),
        "source": "virtual-plc-gateway",
        "sequence_id": f'PLC-{snapshot["machine_id"]}-{int(snapshot["heartbeat"])}',
    }


class PLCGateway:
    """Read a PLC, normalize the data, and publish it to telemetry ingestion."""

    def __init__(self, plc: VirtualPLC) -> None:
        self.plc = plc

    def configure(self, **kwargs: Any) -> dict[str, Any]:
        return self.plc.configure(**kwargs)

    def scan(self) -> dict[str, Any]:
        snapshot = self.plc.scan()
        telemetry = plc_snapshot_to_telemetry(snapshot)
        ingestion = ingest_reading(telemetry)
        return {
            "plc": snapshot,
            "telemetry": telemetry,
            "ingestion": ingestion,
            "control_write_performed": False,
        }
