from fastapi import APIRouter

from app.schemas.schema_context import SchemaContextRequest
from app.services.schema_context import build_schema_context

router = APIRouter()


@router.post("/schema/context")
def schema_context(payload: SchemaContextRequest):
    return build_schema_context(
        question=payload.question,
        max_tables=payload.max_tables,
    )
