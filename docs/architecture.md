# Architecture

## V1-V1.5

Client / Maintenance System / Dashboard
        |
        v
FastAPI API
        |
        +--> Machine Health Engine
        +--> Telemetry / Machine Data
        +--> Anomaly Detection
        +--> Predictive Maintenance Risk
        +--> Root-Cause Analysis
        +--> Historical Failure Diagnosis
        +--> Failure Pattern Learning
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

## Closed learning loop

Machine -> sensor/production data -> health -> anomaly -> maintenance risk -> root cause -> historical failures -> part lifecycle -> spare recommendation -> technician decision -> replacement record -> new training/evidence data.

This allows future versions to learn actual component life from real replacement outcomes instead of relying only on manufacturer-rated life.

## Important design principle

The system should not automatically replace a part. It should provide evidence:

"Cooling Fan CF-24: 91% runtime life used, 78% production life used, 52% calendar life used. Runtime is the limiting meter. Inspect and plan replacement."

A human maintenance decision remains the final action.
