from __future__ import annotations

from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from app.core.governance import (
    MAX_CTES,
    MAX_JOINS,
    MAX_SET_OPERATIONS,
    MAX_SUBQUERIES,
)
from app.core.schema_catalog import SCHEMA_CATALOG


MAX_RESULT_ROWS = 500

_BLOCKED_NODE_NAMES = (
    "Insert",
    "Update",
    "Delete",
    "Merge",
    "Create",
    "Drop",
    "Alter",
    "TruncateTable",
    "Command",
    "Copy",
    "Grant",
    "Revoke",
    "Transaction",
    "Commit",
    "Rollback",
    "Set",
    "Use",
    "Analyze",
    "Vacuum",
)

BLOCKED_NODE_TYPES = tuple(
    node_type
    for name in _BLOCKED_NODE_NAMES
    if (node_type := getattr(exp, name, None)) is not None
)

BLOCKED_FUNCTION_NAMES = {
    "pg_sleep",
    "pg_read_file",
    "pg_read_binary_file",
    "pg_ls_dir",
    "lo_import",
    "lo_export",
    "dblink",
    "dblink_exec",
}


class SqlValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedSql:
    original_sql: str
    normalized_sql: str
    executable_sql: str
    tables: list[str]
    row_limit: int = MAX_RESULT_ROWS


def _cte_names(tree: exp.Expression) -> set[str]:
    names: set[str] = set()
    for cte in tree.find_all(exp.CTE):
        alias = cte.alias_or_name
        if alias:
            names.add(alias.lower())
    return names


def _validate_statement_type(tree: exp.Expression) -> None:
    if not isinstance(tree, exp.Query):
        raise SqlValidationError("Only read-only SELECT/WITH queries are allowed.")

    if tree.find(exp.Select) is None and not isinstance(tree, exp.Select):
        raise SqlValidationError("Only read-only SELECT/WITH queries are allowed.")

    for node in tree.walk():
        if BLOCKED_NODE_TYPES and isinstance(node, BLOCKED_NODE_TYPES):
            raise SqlValidationError(
                f"Blocked SQL operation detected: {node.__class__.__name__.upper()}."
            )


def _function_name(node: exp.Expression) -> str | None:
    if isinstance(node, exp.Anonymous):
        return (node.name or "").lower()

    if isinstance(node, exp.Func):
        try:
            name = node.sql_name()
        except Exception:
            return None
        return name.lower() if name else None

    return None


def _validate_functions(tree: exp.Expression) -> None:
    for node in tree.walk():
        name = _function_name(node)
        if name in BLOCKED_FUNCTION_NAMES:
            raise SqlValidationError(f"Function '{name}' is not allowed.")


def _validate_tables(tree: exp.Expression) -> list[str]:
    approved = set(SCHEMA_CATALOG)
    ctes = _cte_names(tree)
    used: set[str] = set()

    for table in tree.find_all(exp.Table):
        table_name = (table.name or "").lower()
        schema_name = (table.db or "").lower()

        if table_name in ctes:
            continue

        if schema_name and schema_name != "public":
            raise SqlValidationError(
                f"Schema '{schema_name}' is not approved for InsightPilot."
            )

        if not table_name:
            raise SqlValidationError("Unable to identify a referenced table.")

        if table_name not in approved:
            raise SqlValidationError(
                f"Table '{table_name}' is not approved for InsightPilot."
            )

        used.add(table_name)

    return sorted(used)


def _validate_complexity(tree: exp.Expression) -> None:
    joins = sum(1 for _ in tree.find_all(exp.Join))
    ctes = sum(1 for _ in tree.find_all(exp.CTE))
    subqueries = sum(1 for _ in tree.find_all(exp.Subquery))
    set_operation_types = tuple(
        node_type
        for name in ("Union", "Intersect", "Except")
        if (node_type := getattr(exp, name, None)) is not None
    )
    set_operations = sum(
        1
        for node in tree.walk()
        if set_operation_types and isinstance(node, set_operation_types)
    )

    if joins > MAX_JOINS:
        raise SqlValidationError(
            f"Query complexity limit exceeded: at most {MAX_JOINS} JOINs are allowed."
        )

    if ctes > MAX_CTES:
        raise SqlValidationError(
            f"Query complexity limit exceeded: at most {MAX_CTES} CTEs are allowed."
        )

    if subqueries > MAX_SUBQUERIES:
        raise SqlValidationError(
            f"Query complexity limit exceeded: at most {MAX_SUBQUERIES} subqueries are allowed."
        )

    if set_operations > MAX_SET_OPERATIONS:
        raise SqlValidationError(
            "Query complexity limit exceeded: at most "
            f"{MAX_SET_OPERATIONS} UNION/INTERSECT/EXCEPT operations are allowed."
        )


def _apply_row_limit(tree: exp.Expression, max_rows: int) -> exp.Expression:
    limit = tree.args.get("limit")
    if limit is None:
        return tree.limit(max_rows, copy=False)

    expression = getattr(limit, "expression", None)
    if not isinstance(expression, exp.Literal) or not expression.is_int:
        raise SqlValidationError(
            f"LIMIT must be a numeric value between 1 and {max_rows}."
        )

    requested = int(expression.this)
    if requested < 1:
        raise SqlValidationError("LIMIT must be at least 1.")

    if requested > max_rows:
        tree.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))

    return tree


def validate_sql(sql: str, max_rows: int = MAX_RESULT_ROWS) -> ValidatedSql:
    if not sql or not sql.strip():
        raise SqlValidationError("SQL cannot be empty.")

    if max_rows < 1 or max_rows > MAX_RESULT_ROWS:
        raise SqlValidationError(
            f"max_rows must be between 1 and {MAX_RESULT_ROWS}."
        )

    try:
        statements = sqlglot.parse(sql, read="postgres")
    except ParseError as exc:
        raise SqlValidationError(f"Invalid PostgreSQL SQL: {exc}") from exc

    statements = [statement for statement in statements if statement is not None]

    if len(statements) != 1:
        raise SqlValidationError("Exactly one SQL statement is allowed.")

    tree = statements[0]

    _validate_statement_type(tree)
    _validate_functions(tree)
    _validate_complexity(tree)
    tables = _validate_tables(tree)

    normalized_sql = tree.sql(dialect="postgres", pretty=False)
    tree = _apply_row_limit(tree, max_rows=max_rows)
    executable_sql = tree.sql(dialect="postgres", pretty=False)

    return ValidatedSql(
        original_sql=sql,
        normalized_sql=normalized_sql,
        executable_sql=executable_sql,
        tables=tables,
        row_limit=max_rows,
    )
