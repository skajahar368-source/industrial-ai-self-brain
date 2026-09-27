# Architecture

## V1-V1.7

Client / Maintenance System / Dashboard
        |
        v
FastAPI API
        |
        +--> Machine Health Engine
        +--> Telemetry / Machine Data
        +--> Real-Time Telemetry Ingestion
        +--> Anomaly Detection
        +--> Predictive Maintenance Risk
        +--> Root-Cause Analysis
        +--> Historical Failure Diagnosis
        +--> Failure Pattern Learning
        +--> AI Industrial Assistant
        +--> Part Lifecycle Intelligence
        +--> Spare Parts Intelligence
        |
        v
Maintenance / Production Data Store

## Part lifecycle intelligence

When a technician replaces a component, the maintenance system records:

- machine and part identity
- installation date
- machine runtime at installation
- production cycles at installation
- rated runtime life
- rated production life
- rated calendar life

Self-Brain then compares the installed part against three independent life meters:

1. Calendar age
2. Machine runtime
3. Production cycles

The system calculates utilization and remaining life for each meter.

Lifecycle states:

- healthy
- replacement_due_soon
- replace_now
- unknown when no life limit is configured

A replacement warning is triggered when any configured life meter reaches 75% utilization, and a replacement-due decision is triggered at 100%.

## Failure pattern learning

Self-Brain groups historical breakdowns by machine, cause, fault code, and replaced part. When a new event arrives, it compares the current root-cause evidence with those patterns and produces an evidence-backed confidence score. A strong pattern is a prompt to investigate and verify the cause, not an automatic replacement command.

Verified repair outcomes are stored separately as learning evidence. This lets future versions measure which historical repair patterns actually resolved failures and eventually train supervised failure models when enough labeled data exists.

## Real-time telemetry ingestion

Industrial sources such as PLC gateways, SCADA historians, IoT collectors, or maintenance systems can send normalized telemetry to the ingestion API. The ingestion layer validates required fields and numeric ranges, normalizes timestamps, assigns source metadata, rejects malformed events, and prevents duplicate sequence IDs from being stored. The stored telemetry stream becomes the live input boundary for downstream intelligence.

## AI industrial assistant

The assistant is a grounded orchestration layer over the existing engineering modules. It retrieves the latest machine telemetry, health status, anomaly result, maintenance risk, root-cause evidence, historical failure patterns, and—when requested—part lifecycle and spare inventory context. It does not invent machine facts or issue automatic replacement commands.

The assistant classifies the operator question into an operational intent such as health, diagnosis, history, lifecycle, or spares, then returns both a concise answer and structured evidence for traceability.

## Closed learning loop

Machine -> sensor/production data -> health -> anomaly -> maintenance risk -> root cause -> historical failures -> part lifecycle -> spare recommendation -> technician decision -> replacement record -> new training/evidence data.

This allows future versions to learn actual component life from real replacement outcomes instead of relying only on manufacturer-rated life.

## Important design principle

The system should not automatically replace a part. It should provide evidence:

"Cooling Fan CF-24: 91% runtime life used, 78% production life used, 52% calendar life used. Runtime is the limiting meter. Inspect and plan replacement."

A human maintenance decision remains the final action.
