from app.services.evidence_followup import answer_from_evidence
from app.services.evidence_memory import EvidenceMemory


def test_v2_evidence_is_normalized_with_ids():
    memory = EvidenceMemory()
    snapshot = memory.remember_v2(
        "ses_1",
        {
            "question": "Why did revenue decline?",
            "status": "completed",
            "conclusion": "South declined most.",
            "caveats": ["Association does not prove causality."],
            "plan": {
                "steps": [
                    {
                        "status": "completed",
                        "title": "Regional revenue",
                        "evidence_summary": "South declined 24.77%.",
                        "sql": "SELECT 1",
                        "tables": ["payments", "regions"],
                        "rows": [{"region": "South"}],
                        "row_count": 1,
                    }
                ]
            },
        },
    )

    assert snapshot is not None
    assert snapshot.evidence[0].evidence_id == "E1"
    assert snapshot.evidence[0].title == "Regional revenue"


def test_evidence_request_returns_prior_sql_without_rerun():
    memory = EvidenceMemory()
    snapshot = memory.remember_v2(
        "ses_1",
        {
            "question": "Investigate South.",
            "status": "completed",
            "conclusion": "South declined.",
            "caveats": [],
            "plan": {
                "steps": [
                    {
                        "status": "completed",
                        "title": "Revenue",
                        "evidence_summary": "Revenue declined.",
                        "sql": "SELECT SUM(amount) FROM payments",
                        "tables": ["payments"],
                        "rows": [{"value": 10}],
                        "row_count": 1,
                    }
                ]
            },
        },
    )

    result = answer_from_evidence("evidence_request", "Show SQL.", snapshot)

    assert result.route == "evidence_memory"
    assert result.result["evidence"][0]["sql"] == "SELECT SUM(amount) FROM payments"


def test_challenge_surfaces_caveat_instead_of_claiming_causality():
    memory = EvidenceMemory()
    snapshot = memory.remember_v2(
        "ses_1",
        {
            "question": "Why did revenue decline?",
            "status": "completed",
            "conclusion": "Failures increased.",
            "caveats": ["Failed payments are associated with the decline but do not prove causality."],
            "plan": {"steps": []},
        },
    )

    result = answer_from_evidence(
        "challenge",
        "Are you sure failures caused it?",
        snapshot,
    )

    assert result.status == "completed"
    assert "do not prove causality" in result.result["answer"]


def test_no_prior_evidence_is_explicit():
    result = answer_from_evidence(
        "explanation",
        "Explain this.",
        None,
    )

    assert result.status == "no_evidence"
    assert "no completed evidence" in result.result["answer"].lower()
