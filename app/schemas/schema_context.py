from pydantic import BaseModel, Field


class SchemaContextRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    max_tables: int = Field(default=4, ge=1, le=7)
