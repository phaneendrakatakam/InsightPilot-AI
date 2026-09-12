from __future__ import annotations

from app.schemas.investigation import (
    InvestigationPlan,
    InvestigationResponse,
)
from app.services.gemini_service import generate_investigation_synthesis


MAX_SYNTHESIS_ROWS_PER_STEP = 25


def _completed_evidence_payload(plan: InvestigationPlan) -> tuple[list[dict], bool]:
    payload: list[dict] = []
    any_truncated = False

    for step in plan.steps:
        if step.status != "completed":
            continue

        rows = step.rows[:MAX_SYNTHESIS_ROWS_PER_STEP]
        truncated = len(step.rows) > MAX_SYNTHESIS_ROWS_PER_STEP
        any_truncated = any_truncated or truncated

        payload.append(
            {
                "step_id": step.step_id,
                "title": step.title,
                "objective": step.objective,
                "status": step.status,
                "tables": step.tables,
                "row_count": step.row_count,
                "rows": rows,
                "rows_truncated": truncated,
                "evidence_summary": step.evidence_summary,
            }
        )

    return payload, any_truncated


def _execution_caveats(plan: InvestigationPlan) -> list[str]:
    caveats: list[str] = []

    for step in plan.steps:
        if step.status in {"failed", "blocked"}:
            detail = step.error or f"Step ended with status {step.status}."
            caveats.append(f"{step.title}: {detail}")

    return caveats


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in items if item and item.strip()))


def synthesize_investigation(plan: InvestigationPlan) -> InvestigationResponse:
    evidence_payload, rows_truncated = _completed_evidence_payload(plan)
    execution_caveats = _execution_caveats(plan)

    if not evidence_payload:
        return InvestigationResponse(
            question=plan.question,
            status="failed",
            plan=plan,
            findings=[],
            conclusion=(
                "The investigation could not produce completed database evidence, "
                "so no evidence-backed conclusion can be made."
            ),
            caveats=_dedupe(execution_caveats),
        )

    synthesis = generate_investigation_synthesis(
        question=plan.question,
        evidence_payload=evidence_payload,
    )

    completed_count = len(evidence_payload)
    overall_status = (
        "completed"
        if completed_count == len(plan.steps)
        else "partial"
    )

    caveats = [*synthesis.caveats, *execution_caveats]

    if rows_truncated:
        caveats.append(
            "At least one investigation step returned more rows than the synthesis "
            "context limit; the synthesis used the first 25 rows plus the step's "
            "grounded evidence summary."
        )

    return InvestigationResponse(
        question=plan.question,
        status=overall_status,
        plan=plan,
        findings=synthesis.findings,
        conclusion=synthesis.conclusion,
        caveats=_dedupe(caveats),
    )
