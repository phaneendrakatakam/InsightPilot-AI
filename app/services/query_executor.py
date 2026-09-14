from __future__ import annotations

from time import perf_counter

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.governance import mask_sensitive_rows, report_for_rows
from app.core.sql_guard import ValidatedSql, validate_sql
from app.db.session import engine


class QueryExecutionError(RuntimeError):
    pass


def execute_read_query(sql: str) -> dict:
    validated: ValidatedSql = validate_sql(sql)
    started = perf_counter()

    try:
        with engine.connect() as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            result = connection.execute(text(validated.executable_sql))
            columns = list(result.keys())
            raw_rows = [dict(row) for row in result.mappings().all()]

    except SQLAlchemyError as exc:
        raise QueryExecutionError(
            "The validated read-only query could not be executed."
        ) from exc

    rows, masked_fields = mask_sensitive_rows(
        raw_rows,
        sql=validated.executable_sql,
    )
    governance = report_for_rows(masked_fields)
    elapsed_ms = round((perf_counter() - started) * 1000, 2)

    return {
        "status": "success",
        "sql": validated.executable_sql,
        "tables": validated.tables,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "row_limit": validated.row_limit,
        "execution_time_ms": elapsed_ms,
        "governance": governance.model_dump(mode="json"),
    }
