from __future__ import annotations

from app.schemas.investigation import (
    InvestigationFinding,
    InvestigationPlan,
    InvestigationStep,
    InvestigationSynthesis,
)
from app.services import investigation_service, investigation_synthesizer
from app.prompts.investigation_synthesis import build_investigation_synthesis_prompt


def _completed_step(step_id: str = "step_1", rows=None) -> InvestigationStep:
    return InvestigationStep(
        step_id=step_id,
        title="Revenue movement",
        objective="Compare July and August successful payment revenue.",
        status="completed",
        tables=["payments"],
        row_count=2,
        rows=rows or [
            {"month": "July", "revenue": 1902744},
            {"month": "August", "revenue": 1770795},
        ],
        evidence_summary="Revenue declined from July to August.",
    )


def test_synthesis_prompt_contains_grounding_and_causality_guards():
    prompt = build_investigation_synthesis_prompt(
        "Why did revenue decline?",
        [{"status": "completed", "rows": [{"value": 1}]}],
    )

    assert "Use ONLY the executed evidence" in prompt
    assert "Failed-payment amounts are attempted amounts" in prompt
    assert "Refunds are a separate adverse signal" in prompt
    assert "do not claim direct causality" in prompt


def test_completed_evidence_payload_ignores_failed_steps_and_limits_rows():
    many_rows = [{"n": i} for i in range(30)]
    plan = InvestigationPlan(
        question="Why?",
        investigation_goal="Investigate.",
        steps=[
            _completed_step(rows=many_rows),
            InvestigationStep(
                step_id="step_2",
                title="Blocked",
                objective="Missing evidence.",
                status="blocked",
                tables=["refunds"],
                error="needs clarification",
            ),
        ],
    )

    payload, truncated = investigation_synthesizer._completed_evidence_payload(plan)

    assert len(payload) == 1
    assert len(payload[0]["rows"]) == 25
    assert payload[0]["rows_truncated"] is True
    assert truncated is True


def test_synthesize_returns_failed_without_completed_evidence(monkeypatch):
    plan = InvestigationPlan(
        question="Why?",
        investigation_goal="Investigate.",
        steps=[
            InvestigationStep(
                step_id="step_1",
                title="Revenue",
                objective="Compare revenue.",
                status="failed",
                tables=["payments"],
                error="query failed",
            )
        ],
    )

    def should_not_run(**kwargs):
        raise AssertionError("Gemini synthesis should not run without evidence")

    monkeypatch.setattr(
        investigation_synthesizer,
        "generate_investigation_synthesis",
        should_not_run,
    )

    result = investigation_synthesizer.synthesize_investigation(plan)

    assert result.status == "failed"
    assert result.findings == []
    assert "no evidence-backed conclusion" in result.conclusion
    assert "query failed" in result.caveats[0]


def test_synthesize_returns_completed_when_every_step_completed(monkeypatch):
    plan = InvestigationPlan(
        question="Why did revenue decline?",
        investigation_goal="Investigate.",
        steps=[_completed_step()],
    )

    monkeypatch.setattr(
        investigation_synthesizer,
        "generate_investigation_synthesis",
        lambda **kwargs: InvestigationSynthesis(
            findings=[
                InvestigationFinding(
                    title="Revenue decline",
                    evidence="Successful-payment revenue declined in August.",
                    significance="high",
                )
            ],
            conclusion="The strongest direct observation is the revenue decline.",
            caveats=[],
        ),
    )

    result = investigation_synthesizer.synthesize_investigation(plan)

    assert result.status == "completed"
    assert len(result.findings) == 1
    assert result.caveats == []


def test_synthesize_returns_partial_and_preserves_execution_caveat(monkeypatch):
    plan = InvestigationPlan(
        question="Why did revenue decline?",
        investigation_goal="Investigate.",
        steps=[
            _completed_step(),
            InvestigationStep(
                step_id="step_2",
                title="Refund activity",
                objective="Compare refunds.",
                status="blocked",
                tables=["refunds"],
                error="refund evidence unavailable",
            ),
        ],
    )

    monkeypatch.setattr(
        investigation_synthesizer,
        "generate_investigation_synthesis",
        lambda **kwargs: InvestigationSynthesis(
            findings=[
                InvestigationFinding(
                    title="Revenue decline",
                    evidence="Revenue decreased.",
                    significance="high",
                )
            ],
            conclusion="Evidence is partial.",
            caveats=["One analytical signal remains uncertain."],
        ),
    )

    result = investigation_synthesizer.synthesize_investigation(plan)

    assert result.status == "partial"
    assert "One analytical signal remains uncertain." in result.caveats
    assert any("refund evidence unavailable" in item for item in result.caveats)


def test_investigate_runs_planner_executor_then_synthesizer(monkeypatch):
    plan = InvestigationPlan(
        question="Why did revenue decline?",
        investigation_goal="Investigate.",
        steps=[_completed_step()],
    )
    calls: list[str] = []

    monkeypatch.setattr(
        investigation_service,
        "create_investigation_plan",
        lambda question: calls.append("plan") or plan,
    )
    monkeypatch.setattr(
        investigation_service,
        "execute_investigation_plan",
        lambda incoming: calls.append("execute") or incoming,
    )
    monkeypatch.setattr(
        investigation_service,
        "synthesize_investigation",
        lambda incoming: calls.append("synthesize") or "done",
    )

    result = investigation_service.investigate("Why did revenue decline?")

    assert result == "done"
    assert calls == ["plan", "execute", "synthesize"]
