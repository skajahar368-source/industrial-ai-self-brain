from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="Industrial AI — Self-Brain",
    version="0.1.0",
    description="Prototype API for industrial machine health and predictive-maintenance intelligence.",
)

app.include_router(router)


@app.get("/")
def root() -> dict:
    return {
        "project": "Industrial AI — Self-Brain",
        "version": "0.1.0",
        "status": "online",
    }
