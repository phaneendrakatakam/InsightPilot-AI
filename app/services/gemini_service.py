from __future__ import annotations

from functools import lru_cache

from google import genai
from pydantic import ValidationError

from app.core.config import settings
from app.core.schema_catalog import SCHEMA_CATALOG
from app.prompts.answer_generation import build_answer_generation_prompt
from app.prompts.evidence_reasoning import build_evidence_reasoning_prompt
from app.prompts.investigation_planning import build_investigation_planning_prompt
from app.prompts.investigation_synthesis import build_investigation_synthesis_prompt
from app.prompts.sql_generation import build_sql_generation_prompt
from app.schemas.analytics import EvidenceReasoning
from app.schemas.assistant import EvidenceAnswer, SqlGeneration
from app.schemas.investigation import InvestigationPlan, InvestigationSynthesis


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


INVESTIGATION_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {
            "type": "string",
            "description": "The original business investigation question.",
        },
        "investigation_goal": {
            "type": "string",
            "description": "Concise description of what the investigation must determine.",
        },
        "steps": {
            "type": "array",
            "minItems": 2,
            "maxItems": 6,
            "items": {
                "type": "object",
                "properties": {
                    "step_id": {
                        "type": "string",
                        "description": "Stable identifier such as step_1.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Short business-readable investigation step title.",
                    },
                    "objective": {
                        "type": "string",
                        "description": "Evidence this step must collect.",
                    },
                    "tables": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": sorted(SCHEMA_CATALOG.keys()),
                        },
                        "description": "Approved tables likely relevant to this step.",
                    },
                },
                "required": ["step_id", "title", "objective", "tables"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["question", "investigation_goal", "steps"],
    "additionalProperties": False,
}


INVESTIGATION_SYNTHESIS_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "minItems": 1,
            "maxItems": 6,
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "evidence": {"type": "string"},
                    "significance": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                },
                "required": ["title", "evidence", "significance"],
                "additionalProperties": False,
            },
        },
        "conclusion": {
            "type": "string",
            "description": "Evidence-backed conclusion that respects causality limits.",
        },
        "caveats": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Meaningful evidence limitations only.",
        },
    },
    "required": ["findings", "conclusion", "caveats"],
    "additionalProperties": False,
}


EVIDENCE_REASONING_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": "Grounded explanation or challenge response.",
        },
        "supporting_evidence_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Evidence IDs directly supporting the answer.",
        },
        "limitations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Important limitations or missing proof.",
        },
        "causality_statement": {
            "type": "string",
            "description": "Explicit statement of what is or is not causally established.",
        },
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
            "description": "Qualitative confidence based on evidence directness and completeness.",
        },
    },
    "required": [
        "answer",
        "supporting_evidence_ids",
        "limitations",
        "causality_statement",
        "confidence",
    ],
    "additionalProperties": False,
}


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    if not settings.gemini_api_key.strip():
        raise GeminiServiceError(
            "GEMINI_API_KEY is not configured in the local .env file."
        )
    return genai.Client(api_key=settings.gemini_api_key)


def close_gemini_client() -> None:
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


def _structured_interaction(prompt: str, schema: dict, prefix: str) -> str:
    client = _client()
    try:
        interaction = client.interactions.create(
            model=settings.gemini_model,
            input=prompt,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": schema,
            },
            generation_config={"thinking_level": "low"},
        )
    except Exception as exc:
        raise _provider_error(prefix, exc) from exc

    raw = (interaction.output_text or "").strip()
    if not raw:
        raise GeminiServiceError(f"{prefix} response was empty.")
    return raw


def generate_sql(question: str, schema_prompt_context: str) -> SqlGeneration:
    prompt = build_sql_generation_prompt(
        question=question,
        schema_prompt_context=schema_prompt_context,
    )
    raw = _structured_interaction(
        prompt,
        SQL_GENERATION_SCHEMA,
        "Gemini SQL-generation request failed",
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
    raw = _structured_interaction(
        prompt,
        EVIDENCE_ANSWER_SCHEMA,
        "Gemini evidence-answer request failed",
    )
    try:
        return EvidenceAnswer.model_validate_json(raw)
    except ValidationError as exc:
        raise GeminiServiceError(
            "Gemini returned structured evidence output that could not be parsed: "
            f"{exc}"
        ) from exc


def generate_investigation_plan(question: str) -> InvestigationPlan:
    prompt = build_investigation_planning_prompt(question)
    raw = _structured_interaction(
        prompt,
        INVESTIGATION_PLAN_SCHEMA,
        "Gemini investigation-planning request failed",
    )
    try:
        plan = InvestigationPlan.model_validate_json(raw)
    except ValidationError as exc:
        raise GeminiServiceError(
            "Gemini returned an investigation plan that could not be parsed: "
            f"{exc}"
        ) from exc
    plan.question = question
    return plan


def generate_investigation_synthesis(
    question: str,
    evidence_payload: list[dict],
) -> InvestigationSynthesis:
    if not evidence_payload:
        raise GeminiServiceError(
            "Investigation synthesis requires at least one completed evidence step."
        )

    prompt = build_investigation_synthesis_prompt(
        question=question,
        evidence_payload=evidence_payload,
    )
    raw = _structured_interaction(
        prompt,
        INVESTIGATION_SYNTHESIS_SCHEMA,
        "Gemini investigation-synthesis request failed",
    )
    try:
        return InvestigationSynthesis.model_validate_json(raw)
    except ValidationError as exc:
        raise GeminiServiceError(
            "Gemini returned an investigation synthesis that could not be parsed: "
            f"{exc}"
        ) from exc


def generate_evidence_reasoning(
    user_question: str,
    mode: str,
    source_question: str,
    conclusion: str | None,
    caveats: list[str],
    evidence_payload: list[dict],
) -> EvidenceReasoning:
    if not evidence_payload:
        raise GeminiServiceError(
            "Evidence reasoning requires at least one grounded evidence item."
        )

    prompt = build_evidence_reasoning_prompt(
        user_question=user_question,
        mode=mode,
        source_question=source_question,
        conclusion=conclusion,
        caveats=caveats,
        evidence_payload=evidence_payload,
    )
    raw = _structured_interaction(
        prompt,
        EVIDENCE_REASONING_SCHEMA,
        "Gemini evidence-reasoning request failed",
    )
    try:
        return EvidenceReasoning.model_validate_json(raw)
    except ValidationError as exc:
        raise GeminiServiceError(
            "Gemini returned evidence reasoning that could not be parsed: "
            f"{exc}"
        ) from exc
