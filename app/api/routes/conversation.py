from fastapi import APIRouter, HTTPException, Query, status

from app.core.sql_guard import SqlValidationError
from app.schemas.analytics import TurnTraceSummary
from app.schemas.conversation import (
    ConversationSession,
    CopilotTurnResponse,
    CreateSessionRequest,
    EvidenceSnapshot,
    MessageAcceptedResponse,
    SendMessageRequest,
)
from app.services.assistant import AssistantQuestionError
from app.services.copilot_service import run_copilot_turn
from app.services.evidence_memory import evidence_memory
from app.services.gemini_service import GeminiServiceError
from app.services.investigation_planner import InvestigationPlannerError
from app.services.observability import observability_store
from app.services.query_executor import QueryExecutionError
from app.services.session_store import SessionNotFoundError, session_store

router = APIRouter()


@router.post(
    "/sessions",
    response_model=ConversationSession,
    status_code=status.HTTP_201_CREATED,
)
def create_session(payload: CreateSessionRequest | None = None):
    title = payload.title if payload else None
    return session_store.create(title=title)


@router.get("/sessions", response_model=list[ConversationSession])
def list_sessions(limit: int = Query(default=20, ge=1, le=100)):
    return session_store.list_recent(limit=limit)


@router.get(
    "/observability/recent",
    response_model=list[TurnTraceSummary],
    include_in_schema=False,
)
def recent_observability(
    limit: int = Query(default=50, ge=1, le=200),
):
    return observability_store.recent(limit=limit)


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_session(session_id: str):
    try:
        session_store.delete(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation session not found.",
        ) from exc
    return None


@router.get("/sessions/{session_id}", response_model=ConversationSession)
def get_session(session_id: str):
    try:
        return session_store.get(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation session not found.",
        ) from exc


@router.get(
    "/sessions/{session_id}/evidence",
    response_model=list[EvidenceSnapshot],
)
def get_session_evidence(session_id: str):
    try:
        session_store.get(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation session not found.",
        ) from exc

    return evidence_memory.list_for_session(session_id)


@router.post(
    "/sessions/{session_id}/messages",
    response_model=MessageAcceptedResponse,
)
def add_user_message(
    session_id: str,
    payload: SendMessageRequest,
):
    try:
        return session_store.append_user_message(
            session_id,
            payload.message,
        )
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation session not found.",
        ) from exc


@router.post(
    "/sessions/{session_id}/turns",
    response_model=CopilotTurnResponse,
)
def run_turn(
    session_id: str,
    payload: SendMessageRequest,
):
    try:
        return run_copilot_turn(session_id, payload.message)

    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation session not found.",
        ) from exc

    except AssistantQuestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except InvestigationPlannerError as exc:
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
            detail=(
                "The generated query passed validation but could not "
                "be executed."
            ),
        ) from exc

    except GeminiServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post(
    "/sessions/{session_id}/context/reset",
    response_model=ConversationSession,
)
def reset_session_context(session_id: str):
    try:
        return session_store.reset_context(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation session not found.",
        ) from exc
