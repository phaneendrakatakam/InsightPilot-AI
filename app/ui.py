from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def register_ui(app: FastAPI) -> None:
    """Register the InsightPilot V1 UI without replacing existing API routes."""

    if not any(getattr(route, "path", None) == "/static" for route in app.routes):
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
    async def insightpilot_ui(request: Request):
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "app_name": "InsightPilot AI",
                "phase": "V1 — Data Assistant",
            },
        )
