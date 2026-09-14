from __future__ import annotations

from app.schemas.conversation import CopilotExecution, EvidenceReference, EvidenceSnapshot
from app.services.gemini_service import GeminiServiceError, generate_evidence_reasoning


_METRIC_KEYWORDS = {
    "revenue": ["revenue", "successful payment"],
    "product_revenue": ["product revenue"],
    "failed_payments": ["failed payment", "payment failure"],
    "refunds": ["refund"],
    "cancellations": ["cancellation", "cancelled", "churn"],
    "orders": ["order"],
}


def metric_keywords(metric: str | None) -> list[str]:
    if not metric:
        return []
    return list(_METRIC_KEYWORDS.get(metric, [metric.replace("_", " ")]))


def answer_relevant_followup(
    message: str,
    matches: list[EvidenceReference],
) -> CopilotExecution:
    if not matches:
        return CopilotExecution(
            route="evidence_memory",
            status="no_evidence",
            resolved_question=message.strip(),
            result={
                "answer": "The existing evidence does not contain enough information to answer this follow-up.",
                "evidence": [],
            },
        )

    lines = [
        f"{item.evidence_id} — {item.title}: {item.summary}"
        for item in matches
    ]

    return CopilotExecution(
        route="evidence_memory",
        status="completed",
        resolved_question=message.strip(),
        result={
            "answer": "\n".join(lines),
            "reused_evidence": True,
            "evidence": [item.model_dump(mode="json") for item in matches],
        },
    )


def _evidence_lines(snapshot: EvidenceSnapshot) -> list[str]:
    return [
        f"{item.evidence_id}: {item.summary}"
        for item in snapshot.evidence
        if item.summary
    ]


def _deterministic_fallback(
    intent: str,
    message: str,
    snapshot: EvidenceSnapshot,
) -> CopilotExecution:
    evidence_lines = _evidence_lines(snapshot)

    if intent == "challenge":
        caveats = snapshot.caveats or [
            "The available evidence supports observed relationships but does not by itself prove causality."
        ]
        answer = (
            "The evidence supports the observed result, but not a stronger causal claim. "
            + " ".join(caveats)
        )
        return CopilotExecution(
            route="evidence_memory",
            status="completed",
            resolved_question=message.strip(),
            result={
                "answer": answer,
                "reasoning_mode": "deterministic_fallback",
                "supporting_evidence": evidence_lines,
                "limitations": caveats,
                "causality_statement": (
                    "The stored evidence does not independently prove causality."
                ),
                "confidence": "medium",
                "evidence": [
                    item.model_dump(mode="json")
                    for item in snapshot.evidence
                ],
            },
        )

    answer = snapshot.conclusion or "The latest analysis completed without a conclusion."
    if evidence_lines:
        answer = f"{answer}\n\nEvidence used:\n" + "\n".join(evidence_lines)

    return CopilotExecution(
        route="evidence_memory",
        status="completed",
        resolved_question=message.strip(),
        result={
            "answer": answer,
            "reasoning_mode": "deterministic_fallback",
            "supporting_evidence": evidence_lines,
            "limitations": snapshot.caveats,
            "causality_statement": (
                "No causal claim is made beyond what the stored evidence directly establishes."
            ),
            "confidence": "medium",
            "evidence": [
                item.model_dump(mode="json")
                for item in snapshot.evidence
            ],
        },
    )


def answer_from_evidence(
    intent: str,
    message: str,
    snapshot: EvidenceSnapshot | None,
) -> CopilotExecution:
    if snapshot is None:
        return CopilotExecution(
            route="evidence_memory",
            status="no_evidence",
            resolved_question=message.strip(),
            result={
                "answer": (
                    "There is no completed evidence in this conversation yet. "
                    "Run an analysis or investigation first."
                ),
                "evidence": [],
            },
        )

    if intent == "evidence_request":
        source_confidence = (
            snapshot.confidence.level
            if snapshot.confidence is not None
            else "medium"
        )
        return CopilotExecution(
            route="evidence_memory",
            status="completed",
            resolved_question=message.strip(),
            result={
                "answer": "Here is the grounded evidence from the latest completed analysis.",
                "source_question": snapshot.source_question,
                "conclusion": snapshot.conclusion,
                "caveats": snapshot.caveats,
                "confidence": source_confidence,
                "evidence": [
                    item.model_dump(mode="json")
                    for item in snapshot.evidence
                ],
            },
        )

    if intent not in {"explanation", "challenge"}:
        return _deterministic_fallback(intent, message, snapshot)

    evidence_payload = [
        item.model_dump(mode="json")
        for item in snapshot.evidence
    ]

    try:
        reasoning = generate_evidence_reasoning(
            user_question=message,
            mode=intent,
            source_question=snapshot.source_question,
            conclusion=snapshot.conclusion,
            caveats=snapshot.caveats,
            evidence_payload=evidence_payload,
        )
    except GeminiServiceError:
        return _deterministic_fallback(intent, message, snapshot)

    return CopilotExecution(
        route="evidence_memory",
        status="completed",
        resolved_question=message.strip(),
        result={
            "answer": reasoning.answer,
            "reasoning_mode": "grounded_llm",
            "source_question": snapshot.source_question,
            "supporting_evidence_ids": reasoning.supporting_evidence_ids,
            "limitations": reasoning.limitations,
            "causality_statement": reasoning.causality_statement,
            "confidence": reasoning.confidence,
            "evidence": evidence_payload,
        },
    )
