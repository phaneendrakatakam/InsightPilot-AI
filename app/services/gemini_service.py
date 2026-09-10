from __future__ import annotations

from functools import lru_cache

from google import genai
from pydantic import ValidationError

from app.core.config import settings
from app.prompts.answer_generation import build_answer_generation_prompt
from app.prompts.sql_generation import build_sql_generation_prompt
from app.schemas.assistant import EvidenceAnswer, SqlGeneration


class GeminiServiceError(RuntimeError):
    pass


SQL_GENERATION_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["READY", "NEEDS_CLARIFICATION"],
            "description": "READY when safe SQL can be generated; otherwise NEEDS_CLARIFICATION.",
        },
        "intent": {
            "type": "string",
            "description": "Concise interpretation of the user's business intent.",
        },
        "sql": {
            "type": "string",
            "description": "Exactly one PostgreSQL SELECT/WITH query when status is READY; otherwise an empty string.",
        },
        "message": {
            "type": "string",
            "description": "Clarification message or a short generation note.",
        },
    },
    "required": ["status", "intent", "sql", "message"],
    "additionalProperties": False,
}


EVIDENCE_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": "Concise business answer grounded only in database evidence.",
        },
        "observations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Direct observations supported by returned database evidence.",
        },
        "interpretation": {
            "type": "string",
            "description": "Optional interpretation clearly separated from direct observations.",
        },
        "caveat": {
            "type": "string",
            "description": "Any evidence limitation or uncertainty; empty when none.",
        },
    },
    "required": ["answer", "observations", "interpretation", "caveat"],
    "additionalProperties": False,
}


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    """Return one persistent Gemini client for the application process."""
    if not settings.gemini_api_key.strip():
        raise GeminiServiceError(
            "GEMINI_API_KEY is not configured in the local .env file."
        )

    return genai.Client(api_key=settings.gemini_api_key)


def close_gemini_client() -> None:
    """Close and clear the cached Gemini client, if one was created."""
    if _client.cache_info().currsize:
        try:
            client = _client()
            client.close()
        finally:
            _client.cache_clear()


def _provider_error(prefix: str, exc: Exception) -> GeminiServiceError:
    message = str(exc).strip() or repr(exc)
    return GeminiServiceError(
        f"{prefix}: {exc.__class__.__name__}: {message}"
    )


def generate_sql(
    question: str,
    schema_prompt_context: str,
) -> SqlGeneration:
    prompt = build_sql_generation_prompt(
        question=question,
        schema_prompt_context=schema_prompt_context,
    )

    # Keep a strong reference to the owning client for the full request.
    client = _client()

    try:
        interaction = client.interactions.create(
            model=settings.gemini_model,
            input=prompt,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": SQL_GENERATION_SCHEMA,
            },
            generation_config={
                "thinking_level": "low",
            },
        )
    except Exception as exc:
        raise _provider_error("Gemini SQL-generation request failed", exc) from exc

    raw = (interaction.output_text or "").strip()

    if not raw:
        raise GeminiServiceError(
            "Gemini SQL-generation response was empty."
        )

    try:
        return SqlGeneration.model_validate_json(raw)
    except ValidationError as exc:
        raise GeminiServiceError(
            "Gemini returned structured SQL output that could not be parsed: "
            f"{exc}"
        ) from exc


def generate_business_answer(
    question: str,
    executed_sql: str,
    columns: list[str],
    rows: list[dict],
    row_count: int,
) -> EvidenceAnswer:
    if row_count == 0:
        return EvidenceAnswer(
            answer="The query returned no matching rows.",
            observations=[],
            interpretation="",
            caveat="",
        )

    prompt = build_answer_generation_prompt(
        question=question,
        executed_sql=executed_sql,
        columns=columns,
        rows=rows,
        row_count=row_count,
    )

    # Reuse the same persistent client and keep it strongly referenced.
    client = _client()

    try:
        interaction = client.interactions.create(
            model=settings.gemini_model,
            input=prompt,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": EVIDENCE_ANSWER_SCHEMA,
            },
            generation_config={
                "thinking_level": "low",
            },
        )
    except Exception as exc:
        raise _provider_error("Gemini evidence-answer request failed", exc) from exc

    raw = (interaction.output_text or "").strip()

    if not raw:
        raise GeminiServiceError(
            "Gemini evidence-answer response was empty."
        )

    try:
        return EvidenceAnswer.model_validate_json(raw)
    except ValidationError as exc:
        raise GeminiServiceError(
            "Gemini returned structured evidence output that could not be parsed: "
            f"{exc}"
        ) from exc
