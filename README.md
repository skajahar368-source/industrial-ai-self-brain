# Industrial AI — Self-Brain

An industrial AI prototype for machine-health monitoring, anomaly detection, predictive maintenance, degradation analysis, failure prediction, root-cause assistance, failure-pattern learning, part lifecycle intelligence, and spare-parts management.

## V3.1 — Evidence quality and report validation

The structured investigation report now identifies basic evidence gaps instead of silently treating missing context as a normal result.

- `POST /api/maintenance/investigation-report` returns report version `3.1`.
- `evidence_quality` lists missing timestamp, fault code, or numeric sensor measurements.
- The report counts numeric measurement fields and generated rule-based checks; this is descriptive metadata, not an accuracy or confidence score.
- If the anomaly detector did not provide a label, `anomaly_flagged` is `null` rather than incorrectly reporting `false`.
- Safety flags remain explicit: human review is required, no automatic diagnosis/model update is performed, and no PLC/control writes are performed.

Example request:

```json
{
  "machine_id": "M-001",
  "question": "Investigate the current machine condition and what should maintenance inspect?"
}
```

Focused test:

```bash
PYTHONPATH=. pytest -q tests/test_maintenance_investigation_report.py
```

Full test suite:

```bash
PYTHONPATH=. pytest -q
```

Tests verify software behavior with local or synthetic records only. They do not prove sensor calibration, real-machine diagnostic accuracy, or production safety.
