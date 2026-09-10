from app.services.gemini_service import (
    EVIDENCE_ANSWER_SCHEMA,
    SQL_GENERATION_SCHEMA,
)


def test_sql_generation_schema_contract():
    assert SQL_GENERATION_SCHEMA["type"] == "object"
    assert set(SQL_GENERATION_SCHEMA["required"]) == {
        "status",
        "intent",
        "sql",
        "message",
    }
    assert SQL_GENERATION_SCHEMA["properties"]["status"]["enum"] == [
        "READY",
        "NEEDS_CLARIFICATION",
    ]


def test_evidence_answer_schema_contract():
    assert EVIDENCE_ANSWER_SCHEMA["type"] == "object"
    assert set(EVIDENCE_ANSWER_SCHEMA["required"]) == {
        "answer",
        "observations",
        "interpretation",
        "caveat",
    }
