from fastapi import FastAPI

from app.api.routes.ask import router as ask_router
from app.api.routes.health import router as health_router
from app.api.routes.investigate import router as investigate_router
from app.api.routes.query import router as query_router
from app.api.routes.schema import router as schema_router
from app.core.config import settings
from app.core.version import APP_VERSION
from app.ui import register_ui

app = FastAPI(
    title=settings.app_name,
    version=APP_VERSION,
    description="InsightPilot AI — Enterprise Data Investigation & Analytics Agent",
)

app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(schema_router, prefix="/api/v1", tags=["Schema"])
app.include_router(query_router, prefix="/api/v1", tags=["Query Safety"])
app.include_router(ask_router, prefix="/api/v1", tags=["InsightPilot V1"])
app.include_router(
    investigate_router,
    prefix="/api/v2",
    tags=["Investigation Agent"],
)

register_ui(app)
