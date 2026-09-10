from pydantic import BaseModel, Field


class SqlRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=20_000)
