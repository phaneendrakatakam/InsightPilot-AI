from __future__ import annotations

import re

from app.schemas.conversation import ConversationContext

_MONTHS = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)

_REGION_PATTERN = re.compile(r"\b(north|south|east|west)\b", re.IGNORECASE)
_PLAN_PATTERN = re.compile(r"\b(basic|pro|enterprise)\b", re.IGNORECASE)
_MONTH_PATTERN = re.compile(
    r"\b(" + "|".join(_MONTHS) + r")\b",
    re.IGNORECASE,
)

_METRIC_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "failed_payments",
        re.compile(
            r"\b(failed payments?|payment failures?|failures?|failed transactions?)\b",
            re.IGNORECASE,
        ),
    ),
    ("refunds", re.compile(r"\brefunds?\b", re.IGNORECASE)),
    ("cancellations", re.compile(r"\b(cancellations?|churn)\b", re.IGNORECASE)),
    ("product_revenue", re.compile(r"\bproduct revenue\b", re.IGNORECASE)),
    ("revenue", re.compile(r"\brevenue\b", re.IGNORECASE)),
    ("orders", re.compile(r"\borders?\b", re.IGNORECASE)),
)

_DIMENSION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("subscription_plan", re.compile(r"\b(by|per)\s+(subscription\s+)?plan\b", re.IGNORECASE)),
    ("region", re.compile(r"\b(by|per)\s+region\b", re.IGNORECASE)),
    ("product", re.compile(r"\b(by|per)\s+product\b", re.IGNORECASE)),
    ("month", re.compile(r"\b(by|per)\s+month\b", re.IGNORECASE)),
)

_META_REASONING_PATTERN = re.compile(
    r"^\s*(?:"
    r"explain\b|"
    r"show\s+(?:me\s+)?(?:the\s+)?(?:evidence|sql)\b|"
    r"what\s+(?:is|was)\s+the\s+evidence\b|"
    r"are\s+you\s+sure\b|"
    r"how\s+sure\b|"
    r"prove\b|"
    r"can\s+you\s+prove\b|"
    r"is\s+that\s+causal\b|"
    r"did\s+.*\s+cause\s+(?:it|this|that)\b"
    r")",
    re.IGNORECASE,
)


def _is_meta_reasoning_request(message: str) -> bool:
    """Whether the user is inspecting/challenging the current result.

    These turns may mention another metric as part of a causal challenge
    ("Are you sure payment failures caused it?"), but that mention must not
    silently replace the active analytical metric in conversation context.
    """
    return _META_REASONING_PATTERN.search(message or "") is not None



def _canonical(value: str) -> str:
    return value.strip().title()


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def update_conversation_context(
    current: ConversationContext,
    message: str,
) -> ConversationContext:
    """Update explicit analytical context while preserving omitted prior context."""
    updated = current.model_copy(deep=True)
    text = message.strip()
    lower = text.lower()

    updated.last_user_message = text
    updated.revision += 1

    is_meta_request = _is_meta_reasoning_request(text)

    # Explain/challenge/evidence/SQL-inspection turns refer to the current
    # analytical state. They may repeat region/metric words as references,
    # but must not silently rewrite the active analysis context.
    if not is_meta_request:
        for metric, pattern in _METRIC_PATTERNS:
            if pattern.search(text):
                updated.metric = metric
                break

        regions = _unique(
            [_canonical(item) for item in _REGION_PATTERN.findall(text)]
        )

        if len(regions) >= 2:
            # Explicit two-region comparison: "Compare South with North."
            updated.comparison_regions = regions[:2]
            updated.region = None
        elif len(regions) == 1:
            explicit_region = regions[0]

            # Pronoun-based comparison: "Compare it with North."
            # A plain "Now compare North." means switch the active region.
            pronoun_comparison = re.search(
                r"\bcompare\s+(it|this|that)\s+(with|to|against)\b",
                lower,
            ) is not None

            if (
                pronoun_comparison
                and current.region
                and current.region != explicit_region
            ):
                updated.comparison_regions = [
                    current.region,
                    explicit_region,
                ]
                updated.region = None
            else:
                updated.region = explicit_region
                updated.comparison_regions = []

        plans = _unique(
            [item.upper() for item in _PLAN_PATTERN.findall(text)]
        )

        if len(plans) >= 2:
            updated.comparison_plans = plans[:2]
            updated.subscription_plan = None
        elif len(plans) == 1:
            explicit_plan = plans[0]

            pronoun_plan_comparison = re.search(
                r"\bcompare\s+(it|this|that)\s+(with|to|against)\b",
                lower,
            ) is not None

            if (
                pronoun_plan_comparison
                and current.subscription_plan
                and current.subscription_plan != explicit_plan
            ):
                updated.comparison_plans = [
                    current.subscription_plan,
                    explicit_plan,
                ]
                updated.subscription_plan = None
            else:
                updated.subscription_plan = explicit_plan
                updated.comparison_plans = []

        months = [
            _canonical(match)
            for match in _MONTH_PATTERN.findall(text)
        ]
        if len(months) >= 2:
            updated.primary_period = months[0]
            updated.comparison_period = months[1]
        elif len(months) == 1:
            updated.primary_period = months[0]

        for dimension, pattern in _DIMENSION_PATTERNS:
            if pattern.search(text):
                updated.drilldown_dimension = dimension
                break

    return updated


def reset_conversation_context() -> ConversationContext:
    return ConversationContext()
