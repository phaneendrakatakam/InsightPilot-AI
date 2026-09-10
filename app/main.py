from fastapi import FastAPI
from app.ui import register_ui

from app.api.routes.ask import router as ask_router
from app.api.routes.health import router as health_router
from app.api.routes.query import router as query_router
from app.api.routes.schema import router as schema_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="InsightPilot AI — Enterprise Data Investigation & Analytics Agent",
)

app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(schema_router, prefix="/api/v1", tags=["Schema"])
app.include_router(query_router, prefix="/api/v1", tags=["Query Safety"])
app.include_router(ask_router, prefix="/api/v1", tags=["InsightPilot"])


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "phase": "V1 — Data Assistant Foundation",
    }

# InsightPilot V1 web interface
register_ui(app)
