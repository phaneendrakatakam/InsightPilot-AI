from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.schemas.analytics import KpiCard


_TIME_FIELDS = (
    "payment_month",
    "refund_month",
    "cancellation_month",
    "order_month",
    "month",
    "period",
    "date",
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


def _period(row: dict[str, Any]) -> str | None:
    for field in _TIME_FIELDS:
        value = row.get(field)
        if value is not None:
            if isinstance(value, (date, datetime)):
                return value.isoformat()
            return str(value)
    return None


def _meta(field: str) -> tuple[str, str] | None:
    if field in _FIELD_META:
        return _FIELD_META[field]
    return None


def _direction(delta: float | None) -> str:
    if delta is None:
        return "neutral"
    if abs(delta) < 1e-12:
        return "flat"
    return "up" if delta > 0 else "down"


def _comparison_card(
    field: str,
    previous_row: dict[str, Any],
    current_row: dict[str, Any],
    evidence_id: str | None,
) -> KpiCard | None:
    meta = _meta(field)
    if meta is None:
        return None

    previous = _number(previous_row.get(field))
    current = _number(current_row.get(field))
    if previous is None or current is None:
        return None

    delta = current - previous
    percent_change = None if previous == 0 else (delta / previous) * 100

    return KpiCard(
        key=field,
        label=meta[0],
        value=round(current, 4),
        previous_value=round(previous, 4),
        delta=round(delta, 4),
        percent_change=None if percent_change is None else round(percent_change, 2),
        direction=_direction(delta),
        current_period=_period(current_row),
        previous_period=_period(previous_row),
        unit=meta[1],
        evidence_id=evidence_id,
    )


def _single_card(
    field: str,
    row: dict[str, Any],
    evidence_id: str | None,
) -> KpiCard | None:
    meta = _meta(field)
    if meta is None:
        return None

    value = _number(row.get(field))
    if value is None:
        return None

    return KpiCard(
        key=field,
        label=meta[0],
        value=round(value, 4),
        current_period=_period(row),
        unit=meta[1],
        evidence_id=evidence_id,
    )


def _cards_from_rows(
    rows: list[dict[str, Any]],
    evidence_id: str | None,
) -> list[KpiCard]:
    if not rows:
        return []

    candidate_fields = [
        field
        for field in rows[0].keys()
        if _meta(field) is not None
    ]

    if len(rows) == 2:
        cards = [
            card
            for field in candidate_fields
            if (card := _comparison_card(field, rows[0], rows[1], evidence_id))
        ]
        if cards:
            return cards

    if len(rows) == 1:
        return [
            card
            for field in candidate_fields
            if (card := _single_card(field, rows[0], evidence_id))
        ]

    return []


def build_kpis(route: str, result: dict[str, Any]) -> list[KpiCard]:
    """Create deterministic KPI cards only from executed query evidence."""
    cards: list[KpiCard] = []

    if route == "v2_investigation":
        steps = ((result.get("plan") or {}).get("steps") or [])
        for index, step in enumerate(steps, start=1):
            if step.get("status") != "completed":
                continue
            cards.extend(
                _cards_from_rows(
                    list(step.get("rows") or []),
                    evidence_id=f"E{index}",
                )
            )

    elif route == "v1_simple_query":
        evidence = result.get("evidence") or {}
        cards.extend(
            _cards_from_rows(
                list(evidence.get("rows") or []),
                evidence_id="E1",
            )
        )

    # Keep first occurrence of a metric so the response stays minimal.
    unique: dict[str, KpiCard] = {}
    for card in cards:
        unique.setdefault(card.key, card)

    return list(unique.values())
