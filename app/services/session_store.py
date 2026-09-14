from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from app.schemas.conversation import (
    ConversationMessage,
    ConversationSession,
    MessageAcceptedResponse,
)
from app.services.context_manager import (
    reset_conversation_context,
    update_conversation_context,
)
from app.services.intent_router import classify_intent
from app.services.runtime_store import RuntimeStore, runtime_store


class SessionNotFoundError(KeyError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _session_id() -> str:
    return f"ses_{uuid4().hex}"


def _message_id() -> str:
    return f"msg_{uuid4().hex}"


def _default_title(message: str) -> str:
    compact = " ".join(message.split())
    return compact[:72] if compact else "New Investigation"


class SessionStore:
    """Thread-safe, SQLite-backed V3 conversation store."""

    def __init__(self, repository: RuntimeStore | None = None) -> None:
        self._repository = repository or runtime_store
        self._lock = RLock()

    def _save(self, session: ConversationSession) -> None:
        self._repository.save_session(
            session_id=session.session_id,
            payload_json=session.model_dump_json(),
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
        )

    def create(self, title: str | None = None) -> ConversationSession:
        now = _utcnow()
        session = ConversationSession(
            session_id=_session_id(),
            title=(title or "").strip() or "New Investigation",
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._save(session)
        return session.model_copy(deep=True)

    def get(self, session_id: str) -> ConversationSession:
        with self._lock:
            payload = self._repository.get_session(session_id)
            if payload is None:
                raise SessionNotFoundError(session_id)
            return ConversationSession.model_validate_json(payload)

    def list_recent(self, limit: int = 20) -> list[ConversationSession]:
        with self._lock:
            payloads = self._repository.list_sessions(limit=limit)
            return [
                ConversationSession.model_validate_json(payload)
                for payload in payloads
            ]

    def append_user_message(
        self,
        session_id: str,
        content: str,
    ) -> MessageAcceptedResponse:
        with self._lock:
            session = self.get(session_id)

            now = _utcnow()
            message = ConversationMessage(
                message_id=_message_id(),
                role="user",
                content=content.strip(),
                created_at=now,
            )

            if not session.messages and session.title == "New Investigation":
                session.title = _default_title(message.content)

            previous = session.context.model_copy(deep=True)
            resolved = update_conversation_context(previous, message.content)
            intent = classify_intent(message.content, previous, resolved)

            session.messages.append(message)
            session.context = resolved
            session.updated_at = now
            self._save(session)

            return MessageAcceptedResponse(
                session_id=session.session_id,
                message=message.model_copy(deep=True),
                intent=intent,
                context=resolved.model_copy(deep=True),
            )

    def append_assistant_message(
        self,
        session_id: str,
        content: str,
    ) -> ConversationMessage:
        with self._lock:
            session = self.get(session_id)

            message = ConversationMessage(
                message_id=_message_id(),
                role="assistant",
                content=content.strip(),
                created_at=_utcnow(),
            )
            session.messages.append(message)
            session.updated_at = message.created_at
            self._save(session)
            return message.model_copy(deep=True)

    def reset_context(self, session_id: str) -> ConversationSession:
        with self._lock:
            session = self.get(session_id)
            session.context = reset_conversation_context()
            session.updated_at = _utcnow()
            self._save(session)
            return session.model_copy(deep=True)

    def delete(self, session_id: str) -> None:
        with self._lock:
            if not self._repository.delete_session_bundle(session_id):
                raise SessionNotFoundError(session_id)

    def clear(self) -> None:
        with self._lock:
            self._repository.clear_sessions()


session_store = SessionStore(repository=runtime_store)
