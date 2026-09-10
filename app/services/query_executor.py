from __future__ import annotations

from time import perf_counter

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.sql_guard import ValidatedSql, validate_sql
from app.db.session import engine


class QueryExecutionError(RuntimeError):
    pass


def execute_read_query(sql: str) -> dict:
    validated: ValidatedSql = validate_sql(sql)

    started = perf_counter()

    try:
        with engine.connect() as connection:
            # Defense-in-depth: the DB role already defaults to read-only,
            # but each execution explicitly uses a read-only transaction too.
            connection.execute(text("SET TRANSACTION READ ONLY"))

            result = connection.execute(text(validated.executable_sql))
            columns = list(result.keys())
            rows = [dict(row) for row in result.mappings().all()]

    except SQLAlchemyError as exc:
        raise QueryExecutionError(
            "The validated read-only query could not be executed."
        ) from exc

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
    }
