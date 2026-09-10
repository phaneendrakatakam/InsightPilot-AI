from app.prompts.sql_generation import build_sql_generation_prompt
from app.services.schema_context import build_schema_context


def test_write_request_prompt_requires_safe_alternative():
    question = "Delete all inactive customers."
    context = build_schema_context(question)

    prompt = build_sql_generation_prompt(
        question=question,
        schema_prompt_context=context["prompt_context"],
    )

    prompt_lower = prompt.lower()

    assert "read-only refusal rule" in prompt_lower
    assert "offer a safe read-only alternative whenever possible." in prompt_lower
    assert "identify/list" in prompt_lower
    assert "inactive customers" in prompt_lower
    assert "do not generate write sql even as an example." in prompt_lower
