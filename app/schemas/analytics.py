from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class KpiCard(BaseModel):
    key: str
    label: str
    value: float
    previous_value: float | None = None
    delta: float | None = None
    percent_change: float | None = None
    direction: Literal["up", "down", "flat", "neutral"] = "neutral"
    current_period: str | None = None
    previous_period: str | None = None
    unit: Literal["currency", "count", "number"] = "number"
    evidence_id: str | None = None


class ChartSeries(BaseModel):
    key: str
    label: str
    values: list[float] = Field(default_factory=list)
    unit: Literal["currency", "count", "number"] = "number"


class ChartSpec(BaseModel):
    chart_id: str
    title: str
    chart_type: Literal["line", "bar"]
    labels: list[str] = Field(default_factory=list)
    series: list[ChartSeries] = Field(default_factory=list)
    evidence_id: str | None = None


class EvidenceReasoning(BaseModel):
    answer: str
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    causality_statement: str
    confidence: Literal["high", "medium", "low"]


class GovernanceReport(BaseModel):
    status: Literal["passed", "masked", "blocked"] = "passed"
    policy_version: str = "v3.1"
    masked_fields: list[str] = Field(default_factory=list)
    blocked_reason: str | None = None
    query_limits: dict[str, int] = Field(
        default_factory=lambda: {
            "max_result_rows": 500,
            "max_joins": 10,
            "max_ctes": 8,
            "max_subqueries": 10,
            "max_set_operations": 6,
        }
    )


class ProvenanceItem(BaseModel):
    evidence_id: str
    source_route: Literal[
        "v1_simple_query",
        "v2_investigation",
        "evidence_memory",
    ]
    source_question: str
    tables: list[str] = Field(default_factory=list)
    row_count: int = 0
    sql_fingerprint: str | None = None
    query_time_ms: float | None = None
    grounding: Literal["executed_sql", "stored_evidence"] = "executed_sql"


class ConfidenceAssessment(BaseModel):
    level: Literal["high", "medium", "low"]
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    causality_status: Literal[
        "not_applicable",
        "not_established",
        "association_only",
        "contribution_supported",
    ] = "not_applicable"
    causality_note: str


class TurnTraceSummary(BaseModel):
    trace_id: str
    session_id: str
    intent: str
    route: str
    status: str
    started_at: datetime
    duration_ms: float
    query_count: int = 0
    query_time_ms: float = 0.0
    evidence_count: int = 0
    evidence_reused: bool = False
    retry_count: int = 0
    governance_status: Literal["passed", "masked", "blocked"] = "passed"
    error_class: str | None = None
