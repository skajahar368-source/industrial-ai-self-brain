# Industrial AI — Self-Brain

An industrial AI system designed around machine health monitoring, anomaly detection, predictive maintenance, root-cause assistance, failure-pattern learning, part lifecycle intelligence, and spare-parts management.

## Vision

Machine -> Sensors/Data -> AI/ML -> Diagnosis -> Recommendation -> Human/Action -> Learning

## V1 MVP

- Machine health monitoring
- Sensor-data simulation
- Rule-based health status
- Anomaly detection foundation
- Maintenance recommendation foundation
- Part lifecycle and spare-management data model
- API and dashboard-ready project structure

## Roadmap

1. Machine monitoring and synthetic data
2. ML anomaly detection
3. Predictive maintenance
4. Failure-pattern learning
5. AI industrial assistant
6. Real-time industrial integration
7. Supervised failure prediction and remaining-useful-life models

## Tech Stack

Python, Pandas, NumPy, scikit-learn, FastAPI, SQLite/PostgreSQL-ready architecture, and a future React dashboard.

## Disclaimer

This is a portfolio and engineering prototype. It is not intended to control production equipment without appropriate industrial validation and safety controls.

## V1.6 AI Industrial Assistant

The system now exposes a grounded industrial assistant at `POST /api/assistant/ask`. It combines the latest machine reading with health status, anomaly detection, maintenance risk, root-cause evidence, historical failure patterns, lifecycle data when supplied, and spare information. Responses cite the underlying evidence in the API payload and keep the human maintenance decision final.

## V1.2 Predictive Maintenance

The MVP now calculates an explainable 0-100 maintenance-risk score using sensor values, downtime, and fault codes. The API exposes both single-reading scoring and historical telemetry scoring. A future supervised model can replace this transparent baseline once labeled maintenance/failure history is available.
