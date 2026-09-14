from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, Field

from app.schemas.analytics import (
    ChartSpec,
    ConfidenceAssessment,
    GovernanceReport,
    KpiCard,
    ProvenanceItem,
    TurnTraceSummary,
)


ConversationIntent: TypeAlias = Literal[
    "simple_query",
    "investigation",
    "follow_up",
    "comparison",
    "drill_down",
    "explanation",
    "challenge",
    "evidence_request",
]

ExecutionRoute: TypeAlias = Literal[
    "v1_simple_query",
    "v2_investigation",
    "evidence_memory",
    "governance",
]


class ConversationContext(BaseModel):
    metric: str | None = None
    region: str | None = None
    comparison_regions: list[str] = Field(default_factory=list)
    product: str | None = None
    subscription_plan: str | None = None
    comparison_plans: list[str] = Field(default_factory=list)
    drilldown_dimension: Literal[
        "region",
        "subscription_plan",
        "product",
        "month",
    ] | None = None
    primary_period: str | None = None
    comparison_period: str | None = None
    active_investigation_id: str | None = None
    last_user_message: str | None = None
    revision: int = 0


class IntentDecision(BaseModel):
    intent: ConversationIntent
    confidence: Literal["high", "medium", "low"]
    uses_prior_context: bool
    reason: str


class ConversationMessage(BaseModel):
    message_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class ConversationSession(BaseModel):
    session_id: str
    title: str
    messages: list[ConversationMessage] = Field(default_factory=list)
    context: ConversationContext = Field(default_factory=ConversationContext)
    created_at: datetime
    updated_at: datetime


class CreateSessionRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)


class SendMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class MessageAcceptedResponse(BaseModel):
    session_id: str
    message: ConversationMessage
    intent: IntentDecision
    context: ConversationContext


class EvidenceReference(BaseModel):
    evidence_id: str
    title: str
    summary: str
    sql: str | None = None
    tables: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int | None = None
    execution_time_ms: float | None = None
    governance: GovernanceReport | None = None


class EvidenceSnapshot(BaseModel):
    snapshot_id: str
    session_id: str
    source_route: Literal["v1_simple_query", "v2_investigation"]
    source_question: str
    conclusion: str | None = None
    caveats: list[str] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    governance: GovernanceReport = Field(default_factory=GovernanceReport)
    provenance: list[ProvenanceItem] = Field(default_factory=list)
    confidence: ConfidenceAssessment | None = None
    created_at: datetime


class CopilotExecution(BaseModel):
    route: ExecutionRoute
    status: Literal[
        "completed",
        "needs_clarification",
        "no_evidence",
        "blocked",
    ]
    resolved_question: str
    result: dict[str, Any] = Field(default_factory=dict)
    kpis: list[KpiCard] = Field(default_factory=list)
    charts: list[ChartSpec] = Field(default_factory=list)
    provenance: list[ProvenanceItem] = Field(default_factory=list)
    confidence: ConfidenceAssessment | None = None
    governance: GovernanceReport = Field(default_factory=GovernanceReport)
    trace: TurnTraceSummary | None = None


class CopilotTurnResponse(BaseModel):
    session_id: str
    user_message: ConversationMessage
    assistant_message: ConversationMessage
    intent: IntentDecision
    context: ConversationContext
    execution: CopilotExecution
