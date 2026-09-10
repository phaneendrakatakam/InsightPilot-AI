from fastapi import APIRouter, HTTPException, status

from app.core.sql_guard import SqlValidationError, validate_sql
from app.schemas.query import SqlRequest
from app.services.query_executor import QueryExecutionError, execute_read_query

router = APIRouter()


@router.post("/query/validate")
def validate_query(payload: SqlRequest):
    try:
        validated = validate_sql(payload.sql)
        return {
            "valid": True,
            "normalized_sql": validated.normalized_sql,
            "executable_sql": validated.executable_sql,
            "tables": validated.tables,
            "row_limit": validated.row_limit,
        }
    except SqlValidationError as exc:
        return {
            "valid": False,
            "error": str(exc),
        }


@router.post("/query/execute")
def execute_query(payload: SqlRequest):
    try:
        return execute_read_query(payload.sql)

    except SqlValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except QueryExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
