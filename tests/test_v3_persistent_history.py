from pathlib import Path

from app.services.evidence_memory import EvidenceMemory
from app.services.runtime_store import RuntimeStore
from app.services.session_store import SessionStore


def test_session_survives_store_recreation(tmp_path: Path):
    database = tmp_path / "state.db"

    first_repository = RuntimeStore(database)
    first = SessionStore(first_repository)

    session = first.create()
    first.append_user_message(
        session.session_id,
        "Why did revenue decline in August compared with July?",
    )
    first.append_assistant_message(
        session.session_id,
        "Revenue declined in August compared with July.",
    )

    second_repository = RuntimeStore(database)
    second = SessionStore(second_repository)
    restored = second.get(session.session_id)

    assert restored.session_id == session.session_id
    assert restored.context.metric == "revenue"
    assert restored.context.primary_period == "August"
    assert restored.context.comparison_period == "July"
    assert [item.role for item in restored.messages] == ["user", "assistant"]


def test_evidence_survives_store_recreation(tmp_path: Path):
    database = tmp_path / "state.db"

    first_repository = RuntimeStore(database)
    first = EvidenceMemory(first_repository)
    first.remember_v2(
        "ses_persistent",
        {
            "question": "Investigate South.",
            "status": "completed",
            "conclusion": "South revenue declined.",
            "caveats": ["Association does not prove causality."],
            "plan": {
                "steps": [
                    {
                        "status": "completed",
                        "title": "Revenue Movement",
                        "evidence_summary": "Revenue declined.",
                        "sql": "SELECT 1",
                        "tables": ["payments"],
                        "rows": [{"value": 1}],
                        "row_count": 1,
                    }
                ]
            },
        },
    )

    second_repository = RuntimeStore(database)
    second = EvidenceMemory(second_repository)
    restored = second.latest("ses_persistent")

    assert restored is not None
    assert restored.conclusion == "South revenue declined."
    assert restored.evidence[0].evidence_id == "E1"
    assert restored.evidence[0].sql == "SELECT 1"
