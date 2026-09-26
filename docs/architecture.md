# Architecture

## V1

Client / Dashboard
        |
        v
FastAPI
        |
        +--> Health Engine
        +--> Machine Data
        +--> Tooling Data
        +--> ML layer (next phase)
        |
        v
Database (SQLite during MVP, PostgreSQL-ready later)

## ML evolution

Telemetry -> feature engineering -> anomaly detection -> predictive model -> maintenance recommendation.

Model outputs remain explainable and separate from safety-critical control logic.
