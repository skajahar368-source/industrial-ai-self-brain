# Architecture

## V1-V1.3

Client / Dashboard
        |
        v
FastAPI API
        |
        +--> Machine Health Engine
        +--> Telemetry / Machine Data
        +--> Anomaly Detection
        +--> Predictive Maintenance Risk
        +--> Spare Parts Intelligence
        |
        v
Database (SQLite during MVP, PostgreSQL-ready later)

## Intelligence flow

Machine telemetry -> feature engineering -> anomaly detection -> maintenance risk -> spare recommendation.

Maintenance history and spare consumption will later support trained forecasting and failure models.

## Design principles

- Explainable outputs are preferred over opaque recommendations.
- ML predictions remain separate from safety-critical control logic.
- Inventory recommendations include stock, usage, lead time, and criticality.
- Real-time sensor ingestion and event-driven alerts are planned for future versions.
