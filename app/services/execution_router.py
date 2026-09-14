from __future__ import annotations

import re

from app.core.governance import (
    inspect_user_request,
    summarize_result_governance,
)
from app.schemas.conversation import (
    ConversationContext,
    CopilotExecution,
    IntentDecision,
)
from app.services.assistant import answer_question
from app.services.evidence_followup import (
    answer_from_evidence,
    answer_relevant_followup,
    metric_keywords,
)
from app.services.evidence_memory import evidence_memory
from app.services.investigation_service import investigate


_METRIC_LABELS = {
    "revenue": "revenue",
    "product_revenue": "product revenue",
    "failed_payments": "failed payments",
    "refunds": "refunds",
    "cancellations": "subscription cancellations",
    "orders": "orders",
}

_DIMENSION_LABELS = {
    "region": "region",
    "subscription_plan": "subscription plan",
    "product": "product",
    "month": "month",
}


def build_resolved_question(
    message: str,
    context: ConversationContext,
) -> str:
    parts: list[str] = []

    if context.metric:
        parts.append(f"metric: {_METRIC_LABELS.get(context.metric, context.metric)}")

    if context.primary_period and context.comparison_period:
        parts.append(
            f"compare {context.primary_period} with {context.comparison_period}"
        )
    elif context.primary_period:
        parts.append(f"period: {context.primary_period}")

    if len(context.comparison_regions) >= 2:
        parts.append(
            "comparison regions: "
            + " vs ".join(context.comparison_regions[:2])
        )
    elif context.region:
        parts.append(f"region: {context.region}")

    if len(context.comparison_plans) >= 2:
        parts.append(
            "comparison subscription plans: "
            + " vs ".join(context.comparison_plans[:2])
        )
    elif context.subscription_plan:
        parts.append(f"subscription plan: {context.subscription_plan}")

    if context.product:
        parts.append(f"product: {context.product}")

    if context.drilldown_dimension:
        label = _DIMENSION_LABELS.get(
            context.drilldown_dimension,
            context.drilldown_dimension,
        )
        parts.append(f"break down by: {label}")

    if not parts:
        return message.strip()

    return (
        f"{message.strip()}\n"
        f"Established conversational context: {'; '.join(parts)}."
    )


def choose_execution_route(
    intent: IntentDecision,
    message: str,
) -> str:
    if intent.intent in {"explanation", "challenge", "evidence_request"}:
        return "evidence_memory"

    if intent.intent in {"investigation", "drill_down"}:
        return "v2_investigation"

    if intent.intent == "follow_up" and re.search(
        r"\b(why|investigate|drill down|what happened|root cause|break down)\b",
        message,
        flags=re.IGNORECASE,
    ):
        return "v2_investigation"

    return "v1_simple_query"


def execute_intent(
    session_id: str,
    message: str,
    intent: IntentDecision,
    context: ConversationContext,
) -> CopilotExecution:
    request_governance = inspect_user_request(message)

    if request_governance.status == "blocked":
        return CopilotExecution(
            route="governance",
            status="blocked",
            resolved_question=message.strip(),
            result={
                "answer": request_governance.blocked_reason,
                "governance_policy": request_governance.policy_version,
            },
            governance=request_governance,
        )

    route = choose_execution_route(intent, message)

    if route == "evidence_memory":
        snapshot = evidence_memory.latest(session_id)
        execution = answer_from_evidence(
            intent=intent.intent,
            message=message,
            snapshot=snapshot,
        )
        execution.governance = (
            snapshot.governance
            if snapshot is not None
            else request_governance
        )
        return execution

    # Reuse already-grounded evidence before generating a duplicate SQL query.
    if intent.intent == "follow_up":
        keywords = metric_keywords(context.metric)
        matches = evidence_memory.find_relevant(session_id, keywords)
        if matches:
            execution = answer_relevant_followup(message, matches)
            snapshot = evidence_memory.latest(session_id)
            execution.governance = (
                snapshot.governance
                if snapshot is not None
                else request_governance
            )
            return execution

    resolved_question = build_resolved_question(message, context)

    if route == "v2_investigation":
        response = investigate(resolved_question)
        result = response.model_dump(mode="json")
        governance = summarize_result_governance(
            result,
            request_report=request_governance,
        )
        evidence_memory.remember_v2(session_id, result)

        return CopilotExecution(
            route="v2_investigation",
            status="completed",
            resolved_question=resolved_question,
            result=result,
            governance=governance,
        )

    result = answer_question(resolved_question)
    execution_status = (
        "needs_clarification"
        if result.get("status") == "needs_clarification"
        else "completed"
    )
    governance = summarize_result_governance(
        result,
        request_report=request_governance,
    )
    evidence_memory.remember_v1(session_id, result)

    return CopilotExecution(
        route="v1_simple_query",
        status=execution_status,
        resolved_question=resolved_question,
        result=result,
        governance=governance,
    )
