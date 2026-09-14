from __future__ import annotations

import re

from app.schemas.conversation import ConversationContext, IntentDecision


def _has(pattern: str, text: str) -> bool:
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def classify_intent(
    message: str,
    previous_context: ConversationContext,
    resolved_context: ConversationContext,
) -> IntentDecision:
    text = " ".join(message.strip().split())
    lower = text.lower()
    has_history = previous_context.revision > 0

    if _has(
        r"\b(are you sure|prove it|prove that|contradict|could something else|"
        r"another explanation|causality|really caused|actually caused)\b",
        lower,
    ):
        return IntentDecision(
            intent="challenge",
            confidence="high",
            uses_prior_context=has_history,
            reason="The user is challenging a prior analytical conclusion.",
        )

    if (
        _has(
            r"\b(show|give|view|open|inspect)\b.*\b(sql|query|raw rows?|"
            r"evidence|source data|underlying rows?)\b",
            lower,
        )
        or _has(r"\b(sql|raw rows?|underlying evidence)\b", lower)
    ):
        return IntentDecision(
            intent="evidence_request",
            confidence="high",
            uses_prior_context=has_history,
            reason="The user requested inspectable evidence, SQL, or raw rows.",
        )

    if _has(
        r"\b(explain|what does (this|that) mean|why is (this|that) important|"
        r"explain it simply|explain this result|explain this chart)\b",
        lower,
    ):
        return IntentDecision(
            intent="explanation",
            confidence="high",
            uses_prior_context=has_history,
            reason="The user asked for an explanation.",
        )

    if _has(r"^\s*why\b|\b(root cause|what caused|reason for)\b", lower):
        narrowed = has_history and (
            resolved_context.region != previous_context.region
            or resolved_context.product != previous_context.product
            or resolved_context.subscription_plan != previous_context.subscription_plan
            or resolved_context.drilldown_dimension != previous_context.drilldown_dimension
            or _has(r"\b(it|that|there|this)\b", lower)
        )
        if narrowed:
            return IntentDecision(
                intent="drill_down",
                confidence="high",
                uses_prior_context=True,
                reason="A diagnostic follow-up narrows the existing investigation.",
            )
        return IntentDecision(
            intent="investigation",
            confidence="high",
            uses_prior_context=has_history,
            reason="Diagnostic language requires evidence gathering and synthesis.",
        )

    if _has(r"\b(compare|comparison|versus|vs\.?)\b", lower):
        return IntentDecision(
            intent="comparison",
            confidence="high",
            uses_prior_context=has_history,
            reason="The user explicitly requested a comparison.",
        )

    # Supports both "break down South" and "break South down by plan".
    if _has(
        r"\b(investigate|drill down|break down|break\b.{0,60}\bdown|"
        r"dig into|focus on)\b",
        lower,
    ):
        if has_history:
            return IntentDecision(
                intent="drill_down",
                confidence="high",
                uses_prior_context=True,
                reason="The user is narrowing an existing investigation.",
            )
        return IntentDecision(
            intent="investigation",
            confidence="high",
            uses_prior_context=False,
            reason="The user explicitly requested an investigation.",
        )

    if has_history and _has(
        r"\b(what about|how about|and what|what happened there|there too|"
        r"also|now|that|it|those|them|same|what changed most|which changed most|"
        r"biggest change|largest change)\b",
        lower,
    ):
        return IntentDecision(
            intent="follow_up",
            confidence="high",
            uses_prior_context=True,
            reason="The turn refers back to established conversational context.",
        )

    return IntentDecision(
        intent="simple_query",
        confidence="medium",
        uses_prior_context=has_history,
        reason="No higher-order analytical intent signal was detected.",
    )
