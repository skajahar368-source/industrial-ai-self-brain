# Industrial AI — Self-Brain

An industrial AI prototype for machine-health monitoring, anomaly detection, predictive maintenance, degradation analysis, failure prediction, root-cause assistance, failure-pattern learning, part lifecycle intelligence, and spare-parts management.

## Vision

```
Machine / Telemetry
        ↓
   Self-Brain AI/ML
        ↓
Health → Anomaly → Risk → Trend → RCA → Failure Prediction
        ↓
Maintenance Recommendation
        ↓
Human Maintenance Decision
        ↓
Learning / History
```

The system is intentionally **decision-support software**. Human maintenance personnel remain responsible for operational decisions.

## Current implementation

### Real-time telemetry boundary
- Single-reading ingestion at `POST /api/telemetry/ingest`
- Batch ingestion at `POST /api/telemetry/ingest-batch`
- Validation, normalization, UTC timestamps, and duplicate protection
- Deterministic machine telemetry simulation for controlled testing
- Telemetry quality analysis at `POST /api/telemetry/quality` for stale readings, stuck sensors, missing sensor fields, and sudden sensor spikes

### Machine intelligence
- Rule-based machine health evaluation
- Explainable maintenance-risk scoring
- Isolation Forest anomaly detection
- Time-series trend analysis
- Degradation timeline and direction analysis
- Explainable root-cause analysis
- Historical failure diagnosis
- Failure-pattern learning and outcome recording

### Predictive maintenance
- Supervised failure-prediction dataset construction
- Time-based train/test split
- Random Forest failure classifier
- Accuracy, precision, recall, and ROC-AUC metrics when calculable
- Failure-risk prediction with an explicit human-decision requirement
- Model warning that representative labeled machine history is required before operational use

### Machine maintenance intelligence
- Part lifecycle tracking
- Part replacement workflow validation
- Spare inventory and reorder alerts
- Grounded industrial assistant combining current telemetry and maintenance evidence

### Dashboard
A read-only industrial control-room dashboard is available from the FastAPI application. It displays current health, maintenance risk, anomaly status, recent telemetry, trend/degradation information, spare alerts, and the industrial assistant.

### Self-Brain ML layer
- Machine-focused synthetic run-to-failure training data using the existing telemetry schema
- Windowed telemetry features for temperature, pressure, vibration, downtime, and cycle behavior
- Isolation Forest anomaly detection, Random Forest machine-fault classification, and prototype RUL estimation
- Explicit synthetic-data provenance; evaluation metrics are not real-machine accuracy
- API endpoints: `POST /api/self-brain/train`, `GET /api/self-brain/status`, and `POST /api/self-brain/diagnose`
- Human maintenance decision remains mandatory

### Validation Center
The read-only endpoint `GET /api/validation/run` runs deterministic software checks without storing telemetry. The current suite covers:
- normal baseline;
- high temperature;
- high pressure;
- high vibration;
- combined failure;
- negative physical values;
- invalid timestamps;
- missing required telemetry;
- telemetry-quality validation for sudden spikes and stuck sensors;
- multi-step deterioration with trend, degradation, and root-cause checks.

Telemetry quality checks are intentionally separated from machine-health scoring so poor sensor data can be identified before it is treated as a machine condition.

The validation contract distinguishes an expected rejection from an unexpected `ValueError`, so invalid-input tests cannot pass merely because an exception occurred.

## Validation status

The project has an automated end-to-end validation path covering:

1. Simulated normal telemetry
2. Simulated warning telemetry
3. Simulated failure telemetry
4. Telemetry ingestion
5. Dashboard overview
6. Health evaluation
7. Maintenance-risk analysis
8. Trend deterioration
9. Degradation timeline
10. Failure-model training
11. Failure-probability prediction
12. Human-decision requirement

The CI workflow runs the complete pytest suite on Python 3.11.

**Current claim:** the software prototype and simulated end-to-end workflow are working and tested.

**Not yet proven:** production failure-prediction accuracy, real PLC/SCADA/OPC-UA/MQTT integration, representative real-machine failure data, sensor quality, machine-specific baselines, and production safety.

## Validation-first roadmap

- **Validation Center:** deliberately test normal, warning, failure, missing, duplicate, invalid, stale, and contradictory telemetry.
- **V2.4:** integrate Self-Brain ML with telemetry-quality confidence and machine-specific baselines.
- **V2.5:** persistent alarm history with SQLite, restart recovery, and persistence tests.
- **V2.6:** persist human-verified maintenance outcomes and summarize historical repair evidence without automatically retraining models.
- **V3.x:** production-style deployment and real industrial data integration.
- **Future:** PLC/SCADA/OPC-UA/MQTT/IIoT integrations, multi-machine intelligence, stronger RUL models, MLOps, explainability, and digital-twin workflows.

### V2.3: Read-only PLC alarm history

- Track alarm raise, repeat observation, clear, severity, and acknowledgement timestamps.
- Expose `GET /api/plc/alarms` and `GET /api/plc/alarms?machine_id=M-001`.
- Acknowledge an alarm with `POST /api/plc/alarms/acknowledge`, using `machine_id`, `alarm_id`, and `acknowledged_by`.
- Alarm acknowledgement updates only Self-Brain's event log; it does not acknowledge or reset a physical PLC alarm.
- Alarm history is stored in SQLite at `data/alarm_history.sqlite3` by default and survives API process restarts.
- Set `SELF_BRAIN_ALARM_DB` to use a different database path.
- PLC access remains read-only; all responses explicitly report that no control write was performed.

Example acknowledgement payload:

```json
{
  "machine_id": "M-001",
  "alarm_id": "AL-000001",
  "acknowledged_by": "maintenance-technician"
}
```

### V2.4: Industrial Validation Lab

Run the dedicated deterministic fault and stress scenarios:

```bash
PYTHONPATH=. pytest -q tests/industrial_validation
```

The suite covers:
- normal baseline with no active alarm;
- thermal, pressure, vibration, combined, and failure scenarios;
- repeated-fault deduplication;
- recovery and alarm clearing;
- bounded alarm-history behavior under a 100-event stress sequence;
- invalid alarm inputs.

These checks exercise the simulation and software contract only. They do not establish real-machine prediction accuracy, production safety, or compatibility with a physical PLC.

### V2.5: Persistent alarm history

The API now uses SQLite to preserve alarm records across process restarts.

- Alarm raise, repeated observation, clear, and acknowledgement metadata are persisted.
- Alarm IDs continue increasing after restart.
- The alarm history endpoint reads saved records even before a machine gateway is recreated.
- The database path defaults to `data/alarm_history.sqlite3`; set `SELF_BRAIN_ALARM_DB` to override it.
- Direct `AlarmManager()` instances remain in-memory unless a database path is provided, keeping unit tests isolated.
- SQLite persistence is for Self-Brain's event log only. It never sends PLC commands or resets physical alarms.

Persistence tests:

```bash
PYTHONPATH=. pytest -q tests/test_alarm_persistence.py
```

The database is local application state. Back it up according to your deployment requirements; do not commit a live database containing operational records.


### V2.6: Verified maintenance learning

Record maintenance outcomes only after a qualified person has verified the repair result. The records are stored in SQLite at `data/verified_maintenance.sqlite3` by default; set `SELF_BRAIN_MAINTENANCE_DB` to override the path.

- `POST /api/maintenance-learning/outcomes` records the fault, suspected/confirmed cause, repair action, success/failure, verifier, verification method, and result.
- `GET /api/maintenance-learning/insights` summarizes verified cases by machine, fault code, and cause. Optional filters: `machine_id` and `fault_code`.
- Outcomes missing required verification evidence—or explicitly marked `verified: false`—are rejected.
- Insights label their source as `human_verified`; unverified AI suggestions are not included.
- This milestone does **not** automatically retrain a model or turn a historical correlation into a confirmed cause. A human still reviews maintenance recommendations.
- PLC access remains read-only; these endpoints only write Self-Brain's own maintenance-history database.

Example payload:

```json
{
  "event_timestamp": "2026-10-14T10:00:00Z",
  "machine_id": "M-001",
  "fault_code": "HIGH_VIBRATION",
  "cause": "bearing wear",
  "repair_action": "replace bearing",
  "repair_successful": true,
  "verified": true,
  "verified_by": "maintenance-engineer",
  "verification_method": "post-repair vibration measurement",
  "verification_result": "vibration returned to baseline",
  "before_evidence": "vibration high",
  "after_evidence": "vibration normal"
}
```

Run the focused tests:

```bash
PYTHONPATH=. pytest -q tests/test_verified_maintenance_learning.py
```

## Testing

Run locally:

```bash
pip install -r requirements.txt
PYTHONPATH=. pytest -q
```

GitHub Actions runs the same test suite on pushes to `main` and pull requests.

## Safety

This is a portfolio and engineering prototype. It must not directly control production equipment without appropriate industrial validation, cybersecurity controls, safety systems, and qualified engineering review.


## V1.8 PLC-to-Self-Brain prototype

The first end-to-end industrial data path is now implemented:

**Virtual PLC → PLC Gateway → Telemetry API → Health/Risk → Self-Brain ML**

New read-only/development endpoints:
- `GET /api/plc/status`
- `POST /api/plc/configure`
- `POST /api/plc/scan`
- `POST /api/gateway/scan`

`/api/gateway/scan` performs one simulated PLC scan, normalizes and ingests the
telemetry, evaluates machine health and maintenance risk, and—after the ML window
has warmed up—runs the existing Self-Brain diagnosis.

No PLC control write is performed. The prototype remains advisory and simulation-only.


## V1.9 virtual industrial fault lab

The simulator now supports controlled synthetic degradation modes:
- normal
- thermal degradation
- pressure degradation
- vibration / bearing-style degradation
- combined multi-parameter degradation

The dashboard includes an **AI Fault Demo** that runs 24 PLC scans through the
read-only gateway, evaluates health and maintenance risk, performs root-cause
reasoning, and runs Self-Brain ML diagnosis.

This is a software validation environment. The telemetry is synthetic and does
not represent measured limits or real-machine accuracy.


## V2.7 verified-maintenance API validation

API-level tests now exercise the verified-maintenance endpoints across separate route calls:
- persist a verified repair outcome and read it back through the insights endpoint;
- filter insights by machine and normalize fault-code filters;
- reject unverified outcomes without adding them to historical evidence;
- assert the API explicitly reports that no model update or PLC control write occurred.

Run the focused API checks:

```bash
PYTHONPATH=. pytest -q tests/test_maintenance_learning_api.py
```

These tests validate the software contract only. They do not establish real-machine accuracy or production safety.


## V2.8 — Evidence-grounded diagnostic context

The endpoint `POST /api/maintenance-learning/diagnostic-context` returns matching human-verified maintenance history for a machine and fault code, with an optional list of candidate causes to filter by. The response labels records as historical context and explicitly states that history does not prove the current fault's cause.

Example request:

```json
{
  "machine_id": "M-001",
  "fault_code": "HIGH_VIBRATION",
  "causes": ["bearing wear"]
}
```

The response includes matching verified cases, successful repair counts/rates, evidence labels, and an interpretation that warns when no matching evidence exists. It does not generate a diagnosis, update a model, or write to PLC controls.

Run the focused tests:

```bash
PYTHONPATH=. pytest -q tests/test_maintenance_diagnostic_context.py
```



## V2.9 — Verified evidence in the industrial assistant

The industrial assistant now attaches human-verified maintenance records matching the current machine ID and fault code to its evidence payload. When available, its answer summarizes verified cases, successful repair counts, and recorded repair actions. When no matching records exist—or the reading has no usable fault code—it says so instead of guessing.

- The context is labeled as historical evidence, not a diagnosis of the current fault.
- Matching uses the exact machine ID and normalized fault code.
- Evidence comes only from records explicitly marked human-verified.
- No AI model is retrained or modified.
- No PLC/SCADA control writes or machine commands are performed.
- Configure the SQLite history location with `SELF_BRAIN_MAINTENANCE_DB` (default: `data/verified_maintenance.sqlite3`).

Run V2.9 focused tests:

```bash
PYTHONPATH=. pytest -q tests/test_assistant_verified_maintenance_context.py
```

Then run the complete suite:

```bash
PYTHONPATH=. pytest -q
```

These tests validate software behavior with local/synthetic records. They do not establish production diagnostic accuracy or machine safety.


## V3.0 — Structured maintenance investigation report

The new endpoint `POST /api/maintenance/investigation-report` turns the industrial assistant's existing evidence into a structured report with:
- a machine-condition summary from the latest available reading;
- health, maintenance-risk, and anomaly outputs;
- deterministic root-cause rule findings and the checks suggested by those rules;
- separately labeled human-verified maintenance history;
- limitations and explicit human-review requirements.

Example request:

```json
{
  "machine_id": "M-001",
  "question": "Investigate the current machine condition and what should maintenance inspect?"
}
```

The report separates current telemetry, deterministic assessments, and historical verified repairs. It does not claim historical repairs prove the current cause, does not automatically diagnose, does not update a model, and does not write to PLC/SCADA controls. This endpoint is advisory and remains dependent on the quality of available machine data.

Run V3.0 focused tests:

```bash
PYTHONPATH=. pytest -q tests/test_maintenance_investigation_report.py
```

Then run the full suite:

```bash
PYTHONPATH=. pytest -q
```
