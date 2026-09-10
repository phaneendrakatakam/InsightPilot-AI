from typing import Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class SqlGeneration(BaseModel):
    status: Literal["READY", "NEEDS_CLARIFICATION"]
    intent: str
    sql: str
    message: str


class EvidenceAnswer(BaseModel):
    answer: str
    observations: list[str] = Field(default_factory=list)
    interpretation: str = ""
    caveat: str = ""
