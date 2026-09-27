from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router

app = FastAPI(
    title="Industrial AI — Self-Brain",
    version="0.1.8",
    description="Prototype API for industrial machine health and predictive-maintenance intelligence.",
)

app.include_router(router)
app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")


@app.get("/")
def root() -> dict:
    return {
        "project": "Industrial AI — Self-Brain",
        "version": "0.1.8",
        "status": "online",
    }
