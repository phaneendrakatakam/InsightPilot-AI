from fastapi import APIRouter, HTTPException, status

from app.schemas.investigation import InvestigationRequest, InvestigationResponse
from app.services.gemini_service import GeminiServiceError
from app.services.investigation_planner import InvestigationPlannerError
from app.services.investigation_service import investigate

router = APIRouter()


@router.post("/investigate", response_model=InvestigationResponse)
def investigate_business_question(payload: InvestigationRequest):
    try:
        return investigate(payload.question)

    except InvestigationPlannerError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except GeminiServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
