from __future__ import annotations

from datetime import date, datetime
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.schemas.analytics import ChartSeries, ChartSpec


_TIME_FIELDS = (
    "payment_month",
    "refund_month",
    "cancellation_month",
    "order_month",
    "month",
    "period",
    "date",
)

_LABEL_FIELDS = (
    "region_name",
    "product_name",
    "plan_name",
    "subscription_plan",
    "payment_status",
    "order_status",
)

_FIELD_META = {
    "total_revenue": ("Revenue", "currency"),
    "revenue": ("Revenue", "currency"),
    "failed_payment_count": ("Failed Payments", "count"),
    "failed_payment_amount": ("Failed Payment Amount", "currency"),
    "refund_count": ("Refunds", "count"),
    "total_refund_count": ("Refunds", "count"),
    "total_refund_amount": ("Refund Amount", "currency"),
    "cancelled_subscription_count": ("Cancellations", "count"),
    "transaction_count": ("Transactions", "count"),
    "order_count": ("Orders", "count"),
    "quantity": ("Units Sold", "count"),
    "total_quantity": ("Units Sold", "count"),
    "order_amount": ("Order Revenue", "currency"),
    "total_order_amount": ("Order Revenue", "currency"),
}


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(Decimal(value.replace(",", "").strip()))
        except (InvalidOperation, ValueError):
            return None
    return None


def _display(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%b %Y")
    if isinstance(value, date):
        return value.strftime("%b %Y")

    text = str(value)

    # Monthly analytics often arrive as ISO timestamps. Keep chart labels
    # human-readable instead of showing raw 00:00:00 timestamps.
    match = re.match(r"^(\d{4})-(\d{2})(?:-\d{2})?(?:T.*)?$", text)
    if match:
        try:
            parsed = datetime(
                int(match.group(1)),
                int(match.group(2)),
                1,
            )
            return parsed.strftime("%b %Y")
        except ValueError:
            pass

    return text


def _label_field(rows: list[dict[str, Any]]) -> tuple[str | None, bool]:
    if not rows:
        return None, False

    keys = set(rows[0].keys())
    for field in _TIME_FIELDS:
        if field in keys and all(row.get(field) is not None for row in rows):
            return field, True

    for field in _LABEL_FIELDS:
        if field in keys and all(row.get(field) is not None for row in rows):
            return field, False

    return None, False


def _secondary_label_field(
    rows: list[dict[str, Any]],
    primary_field: str,
) -> str | None:
    """Find a second descriptive dimension when primary labels repeat."""
    if not rows:
        return None

    keys = list(rows[0].keys())
    candidates: list[tuple[int, str]] = []

    for field in keys:
        if field == primary_field or field in _FIELD_META:
            continue
        if not all(row.get(field) is not None for row in rows):
            continue

        values = [_display(row[field]) for row in rows]
        if len(set(values)) <= 1:
            continue

        pairs = [
            (_display(row[primary_field]), _display(row[field]))
            for row in rows
        ]

        score = 0
        lower = field.lower()
        if any(token in lower for token in ("month", "date", "period", "year")):
            score += 20
        if len(set(pairs)) == len(rows):
            score += 10

        candidates.append((score, field))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _numeric_fields(rows: list[dict[str, Any]], label_field: str) -> list[str]:
    if not rows:
        return []

    fields: list[str] = []
    for field in rows[0].keys():
        if field == label_field or field not in _FIELD_META:
            continue
        if all(_number(row.get(field)) is not None for row in rows):
            fields.append(field)
    return fields


def _chart_for_rows(
    title: str,
    rows: list[dict[str, Any]],
    evidence_id: str,
    chart_index: int,
) -> ChartSpec | None:
    if len(rows) < 2:
        return None

    label_field, is_time = _label_field(rows)
    if label_field is None:
        return None

    numeric_fields = _numeric_fields(rows, label_field)
    if not numeric_fields:
        return None

    labels = [_display(row[label_field]) for row in rows]

    # A comparison can contain two rows per region (for example July/August).
    # "North, North, South, South" is ambiguous, so add the second dimension.
    if len(set(labels)) < len(labels):
        secondary_field = _secondary_label_field(
            rows,
            primary_field=label_field,
        )
        if secondary_field is not None:
            labels = [
                f"{_display(row[label_field])} · {_display(row[secondary_field])}"
                for row in rows
            ]

    series = []
    for field in numeric_fields[:3]:
        label, unit = _FIELD_META[field]
        series.append(
            ChartSeries(
                key=field,
                label=label,
                values=[float(_number(row[field])) for row in rows],
                unit=unit,
            )
        )

    chart_title = title
    if title == "Query Result" and len(series) == 1:
        chart_title = (
            f"{series[0].label} Movement"
            if is_time
            else f"{series[0].label} Comparison"
        )

    return ChartSpec(
        chart_id=f"chart_{chart_index}",
        title=chart_title,
        chart_type="line" if is_time else "bar",
        labels=labels,
        series=series,
        evidence_id=evidence_id,
    )


def build_charts(route: str, result: dict[str, Any]) -> list[ChartSpec]:
    """Build Chart.js-friendly chart specs only from executed evidence rows."""
    charts: list[ChartSpec] = []

    if route == "v2_investigation":
        steps = ((result.get("plan") or {}).get("steps") or [])
        for index, step in enumerate(steps, start=1):
            if step.get("status") != "completed":
                continue
            chart = _chart_for_rows(
                title=step.get("title") or f"Evidence {index}",
                rows=list(step.get("rows") or []),
                evidence_id=f"E{index}",
                chart_index=len(charts) + 1,
            )
            if chart is not None:
                charts.append(chart)
            if len(charts) >= 4:
                break

    elif route == "v1_simple_query":
        evidence = result.get("evidence") or {}
        chart = _chart_for_rows(
            title="Query Result",
            rows=list(evidence.get("rows") or []),
            evidence_id="E1",
            chart_index=1,
        )
        if chart is not None:
            charts.append(chart)

    return charts
