from fastapi import APIRouter

from app.services.health import evaluate_machine_health

router = APIRouter(prefix="/api")


@router.get("/health")
def api_health() -> dict:
    return {"status": "healthy"}


@router.post("/machine-health")
def machine_health(payload: dict) -> dict:
    return evaluate_machine_health(payload)
