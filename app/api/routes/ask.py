from fastapi import APIRouter, HTTPException, status

from app.core.sql_guard import SqlValidationError
from app.schemas.assistant import AskRequest
from app.services.assistant import AssistantQuestionError, answer_question
from app.services.gemini_service import GeminiServiceError
from app.services.query_executor import QueryExecutionError

router = APIRouter()


@router.post("/ask")
def ask(payload: AskRequest):
    try:
        return answer_question(payload.question)

    except AssistantQuestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except SqlValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Generated SQL was blocked by the safety layer: {exc}",
        ) from exc

    except QueryExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The generated query passed validation but could not be executed.",
        ) from exc

    except GeminiServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
