from __future__ import annotations

import hashlib
import re
from typing import Any

import sqlglot
from sqlglot import exp

from app.schemas.analytics import GovernanceReport


POLICY_VERSION = "v3.1"

MAX_JOINS = 10
MAX_CTES = 8
MAX_SUBQUERIES = 10
MAX_SET_OPERATIONS = 6

_SENSITIVE_SOURCE_COLUMNS = {
    "customer_name",
    "customer_code",
    "email",
    "email_address",
    "phone",
    "phone_number",
    "mobile",
    "mobile_number",
}

_DIRECT_IDENTITY_REQUEST = re.compile(
    r"\b(list|show|give|display|export|download|dump|reveal)\b"
    r".{0,80}\b("
    r"customer\s+names?|customer\s+codes?|emails?|email\s+addresses?|"
    r"phone\s+numbers?|mobile\s+numbers?|pii|personal\s+data"
    r")\b",
    flags=re.IGNORECASE | re.DOTALL,
)


def default_query_limits() -> dict[str, int]:
    return {
        "max_result_rows": 500,
        "max_joins": MAX_JOINS,
        "max_ctes": MAX_CTES,
        "max_subqueries": MAX_SUBQUERIES,
        "max_set_operations": MAX_SET_OPERATIONS,
    }


def inspect_user_request(message: str) -> GovernanceReport:
    """Block direct identity-export requests before SQL generation."""
    if _DIRECT_IDENTITY_REQUEST.search(message or ""):
        return GovernanceReport(
            status="blocked",
            policy_version=POLICY_VERSION,
            blocked_reason=(
                "Direct export of customer identity fields is blocked by the "
                "InsightPilot governance policy. Ask for aggregated or "
                "pseudonymized analysis instead."
            ),
            query_limits=default_query_limits(),
        )

    return GovernanceReport(
        status="passed",
        policy_version=POLICY_VERSION,
        query_limits=default_query_limits(),
    )


def _tokenize_identity(value: Any, prefix: str) -> str:
    if value is None:
        return "[MASKED]"
    token = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:8].upper()
    return f"{prefix}-{token}"


def _sensitive_output_fields(sql: str) -> dict[str, str]:
    """Map each output field to the sensitive source column behind it.

    Keeping the source-column type is important when SQL uses a generic alias,
    such as ``customer_name AS customer``. The alias must still be treated as
    a name and pseudonymized rather than replaced with a generic mask.
    """
    fields: dict[str, str] = {
        column: column
        for column in _SENSITIVE_SOURCE_COLUMNS
    }

    try:
        tree = sqlglot.parse_one(sql, read="postgres")
    except Exception:
        return fields

    for select in tree.find_all(exp.Select):
        for projection in select.expressions:
            source_columns = [
                (column.name or "").lower()
                for column in projection.find_all(exp.Column)
                if (column.name or "").lower() in _SENSITIVE_SOURCE_COLUMNS
            ]
            if not source_columns:
                continue

            alias = (projection.alias_or_name or "").lower().strip()
            if alias:
                fields[alias] = source_columns[0]

    return fields


def _mask_sensitive_value(value: Any, source_column: str) -> str:
    normalized = source_column.lower()

    if "name" in normalized:
        return _tokenize_identity(value, "Customer")

    if "code" in normalized:
        return _tokenize_identity(value, "Code")

    return "[MASKED]"


def mask_sensitive_rows(
    rows: list[dict[str, Any]],
    sql: str = "",
) -> tuple[list[dict[str, Any]], list[str]]:
    """Pseudonymize identity-like fields while preserving analytical distinctness."""
    sensitive_fields = _sensitive_output_fields(sql)
    masked_fields: set[str] = set()
    output: list[dict[str, Any]] = []

    for row in rows:
        masked = dict(row)

        for key, value in row.items():
            normalized = key.lower()
            source_column = sensitive_fields.get(normalized)
            if source_column is None:
                continue

            masked_fields.add(key)
            masked[key] = _mask_sensitive_value(
                value=value,
                source_column=source_column,
            )

        output.append(masked)

    return output, sorted(masked_fields)


def report_for_rows(masked_fields: list[str]) -> GovernanceReport:
    return GovernanceReport(
        status="masked" if masked_fields else "passed",
        policy_version=POLICY_VERSION,
        masked_fields=sorted(set(masked_fields)),
        query_limits=default_query_limits(),
    )


def combine_governance_reports(
    *reports: GovernanceReport | dict | None,
) -> GovernanceReport:
    statuses: list[str] = []
    masked_fields: set[str] = set()
    blocked_reason: str | None = None

    for raw in reports:
        if raw is None:
            continue
        report = (
            raw
            if isinstance(raw, GovernanceReport)
            else GovernanceReport.model_validate(raw)
        )
        statuses.append(report.status)
        masked_fields.update(report.masked_fields)
        blocked_reason = blocked_reason or report.blocked_reason

    if "blocked" in statuses:
        status = "blocked"
    elif "masked" in statuses or masked_fields:
        status = "masked"
    else:
        status = "passed"

    return GovernanceReport(
        status=status,
        policy_version=POLICY_VERSION,
        masked_fields=sorted(masked_fields),
        blocked_reason=blocked_reason,
        query_limits=default_query_limits(),
    )


def summarize_result_governance(
    result: dict[str, Any],
    request_report: GovernanceReport | None = None,
) -> GovernanceReport:
    reports: list[GovernanceReport | dict | None] = [request_report]

    if result.get("governance"):
        reports.append(result["governance"])

    for step in ((result.get("plan") or {}).get("steps") or []):
        if step.get("governance"):
            reports.append(step["governance"])

    return combine_governance_reports(*reports)
