from __future__ import annotations

from app.schemas.investigation import InvestigationResponse
from app.services.investigation_executor import execute_investigation_plan
from app.services.investigation_planner import create_investigation_plan
from app.services.investigation_synthesizer import synthesize_investigation


def investigate(question: str) -> InvestigationResponse:
    """Run the complete V2 investigation pipeline."""
    plan = create_investigation_plan(question)
    executed_plan = execute_investigation_plan(plan)
    return synthesize_investigation(executed_plan)
