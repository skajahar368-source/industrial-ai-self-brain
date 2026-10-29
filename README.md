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

### Virtual PLC simulation (read-only)
- `GET /api/virtual-plc/snapshot?machine_id=M-001&step=10&scenario=warning` returns a deterministic, simulated PLC-style tag snapshot.
- Includes machine state, alarm state, sensor tags, and illustrative register addresses.
- Explicitly reports `real_plc_connected: false` and `write_commands_supported: false`.
- Supports `normal`, `warning`, and `failure` simulation scenarios.
- This endpoint is read-only and never sends commands to real PLCs or machinery.
- `GET /api/virtual-plc/diagnose?machine_id=M-001&step=10&scenario=failure` returns the same simulated snapshot plus explainable, deterministic rule-based findings.
- The diagnosis response explicitly labels its analysis as rule-based (not AI-generated), requires human review, and never performs machine actions.
- `GET /api/virtual-plc/explain?machine_id=M-001&step=10&scenario=failure` adds an optional plain-language explanation from an OpenAI-compatible chat-completions API. The deterministic rule diagnosis remains separate and authoritative for structured findings.
- AI explanations are disabled by default. To enable, set `SELF_BRAIN_LLM_API_KEY`; optionally set `SELF_BRAIN_LLM_BASE_URL` (base URL ending before `/chat/completions`) and `SELF_BRAIN_LLM_MODEL` (defaults to `gpt-4.1-mini`). Use HTTPS. Never commit API keys.
- When no key is configured or the provider is unavailable, the endpoint still returns the simulated snapshot and rule findings with an explicit explanation status. It does not pretend that a rule-based response was generated by AI.
- Provider-generated explanations are unverified advisory text. They cannot issue commands; the endpoint always reports that no real PLC is connected and write commands are unsupported.

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
- **V2.5:** continuous learning using verified maintenance outcomes and failure history.
- **V3.x:** production-style deployment and real industrial data integration.
- **Future:** PLC/SCADA/OPC-UA/MQTT/IIoT integrations, multi-machine intelligence, stronger RUL models, MLOps, explainability, and digital-twin workflows.

## Testing

Run locally:

```bash
pip install -r requirements.txt
PYTHONPATH=. pytest -q
```

GitHub Actions runs the same test suite on pushes to `main` and pull requests.

## Safety

This is a portfolio and engineering prototype. It must not directly control production equipment without appropriate industrial validation, cybersecurity controls, safety systems, and qualified engineering review.
