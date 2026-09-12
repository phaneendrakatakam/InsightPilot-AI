from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class InvestigationRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class InvestigationStep(BaseModel):
    step_id: str
    title: str
    objective: str
    status: Literal["planned", "running", "completed", "failed", "blocked"] = "planned"
    sql: str | None = None
    tables: list[str] = Field(default_factory=list)
    row_count: int | None = None
    rows: list[dict[str, Any]] = Field(default_factory=list)
    evidence_summary: str | None = None
    error: str | None = None


class InvestigationPlan(BaseModel):
    question: str
    investigation_goal: str
    steps: list[InvestigationStep]


class InvestigationFinding(BaseModel):
    title: str
    evidence: str
    significance: Literal["high", "medium", "low"]


class InvestigationSynthesis(BaseModel):
    findings: list[InvestigationFinding] = Field(default_factory=list)
    conclusion: str
    caveats: list[str] = Field(default_factory=list)


class InvestigationResponse(BaseModel):
    question: str
    status: Literal["completed", "partial", "failed"]
    plan: InvestigationPlan
    findings: list[InvestigationFinding] = Field(default_factory=list)
    conclusion: str
    caveats: list[str] = Field(default_factory=list)
