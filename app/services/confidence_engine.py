from __future__ import annotations

import re

from app.schemas.analytics import ConfidenceAssessment, ProvenanceItem
from app.schemas.conversation import CopilotExecution, IntentDecision


_CAUSAL_LANGUAGE = re.compile(
    r"\b(cause|caused|causing|causal|because of|responsible for|drove|driven by)\b",
    flags=re.IGNORECASE,
)


def _limitations(execution: CopilotExecution) -> list[str]:
    result = execution.result or {}

    raw = (
        result.get("limitations")
        or result.get("caveats")
        or []
    )
    limitations = list(raw) if isinstance(raw, list) else []

    if result.get("caveat"):
        limitations.append(str(result["caveat"]))

    if execution.governance.status == "masked":
        limitations.append(
            "Identity-like fields were pseudonymized by governance policy."
        )

    # Preserve order, remove duplicates/empty strings.
    output: list[str] = []
    seen: set[str] = set()
    for item in limitations:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            output.append(text)
    return output


def assess_confidence(
    message: str,
    intent: IntentDecision,
    execution: CopilotExecution,
    provenance: list[ProvenanceItem],
) -> ConfidenceAssessment:
    evidence_ids = [item.evidence_id for item in provenance]
    limitations = _limitations(execution)

    if execution.status in {"blocked", "no_evidence", "needs_clarification"}:
        return ConfidenceAssessment(
            level="low",
            rationale=(
                "The turn did not produce a complete grounded analytical result."
            ),
            evidence_ids=evidence_ids,
            limitations=limitations,
            causality_status="not_applicable",
            causality_note="No causal conclusion is available for this turn.",
        )

    result = execution.result or {}
    route = execution.route

    if route == "evidence_memory" and result.get("confidence") in {
        "high",
        "medium",
        "low",
    }:
        level = result["confidence"]
        rationale = (
            "Confidence follows the grounded evidence-reasoning assessment "
            "from the stored investigation."
        )
    elif route == "v1_simple_query":
        if provenance and all(item.row_count >= 0 for item in provenance):
            level = "high"
            rationale = (
                "The answer is directly grounded in one validated, executed "
                "read-only SQL result."
            )
        else:
            level = "medium"
            rationale = "The answer completed, but provenance is incomplete."
    elif route == "v2_investigation":
        steps = ((result.get("plan") or {}).get("steps") or [])
        completed = sum(1 for step in steps if step.get("status") == "completed")
        failed = sum(
            1 for step in steps
            if step.get("status") in {"failed", "blocked"}
        )

        if completed >= 3 and failed == 0:
            level = "high"
            rationale = (
                "Multiple independent evidence steps completed successfully "
                "without blocked or failed steps."
            )
        elif completed >= 1:
            level = "medium"
            rationale = (
                "The investigation has grounded evidence, but coverage is "
                "partial or limited."
            )
        else:
            level = "low"
            rationale = "No completed investigation evidence is available."
    else:
        level = "medium"
        rationale = "The response is grounded in previously stored evidence."

    conclusion = str(result.get("conclusion") or result.get("answer") or "")
    combined_text = f"{message} {conclusion}"

    if intent.intent == "challenge" or _CAUSAL_LANGUAGE.search(combined_text):
        causality_status = "not_established"
        causality_note = (
            "The available evidence can show association, timing, or measured "
            "contribution, but it does not independently prove a causal mechanism."
        )
    elif (
        "contributor" in conclusion.lower()
        or "contribution" in conclusion.lower()
    ):
        causality_status = "contribution_supported"
        causality_note = (
            "The evidence supports a measured contribution to the observed "
            "change; this should not be interpreted as proof of causation."
        )
    elif intent.intent in {"investigation", "drill_down"} and message.lower().startswith("why"):
        causality_status = "association_only"
        causality_note = (
            "The investigation identifies supported associations and drivers "
            "in the data, not experimentally proven causation."
        )
    else:
        causality_status = "not_applicable"
        causality_note = "This turn does not require a causal claim."

    return ConfidenceAssessment(
        level=level,
        rationale=rationale,
        evidence_ids=evidence_ids,
        limitations=limitations,
        causality_status=causality_status,
        causality_note=causality_note,
    )
