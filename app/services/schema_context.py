from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.schema_catalog import RELATIONSHIPS, SCHEMA_CATALOG


@dataclass(frozen=True)
class TableScore:
    table: str
    score: int


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _term_score(question: str, term: str) -> int:
    """Score exact business-term matches without substring false positives."""
    q = _normalize(question)
    t = _normalize(term)

    if not t:
        return 0

    pattern = rf"(?<!\w){re.escape(t)}(?!\w)"
    if re.search(pattern, q):
        return 3 if " " in t else 2

    q_tokens = set(re.findall(r"[a-z0-9_]+", q))
    t_tokens = set(re.findall(r"[a-z0-9_]+", t))
    if t_tokens and t_tokens.issubset(q_tokens):
        return 1

    return 0


def select_relevant_tables(question: str, max_tables: int = 4) -> list[str]:
    if not question or not question.strip():
        return []

    scores: list[TableScore] = []

    for table_name, metadata in SCHEMA_CATALOG.items():
        score = _term_score(question, table_name)

        for term in metadata["business_terms"]:
            score += _term_score(question, term)

        if score > 0:
            scores.append(TableScore(table=table_name, score=score))

    scores.sort(key=lambda item: (-item.score, item.table))
    selected = [item.table for item in scores[:max_tables]]

    q = _normalize(question)

    wants_customer_dimension = any(
        phrase in q
        for phrase in (
            "customer",
            "customers",
            "region",
            "regions",
            "who",
            "which customer",
            "which region",
        )
    )

    if wants_customer_dimension and "payments" in selected and "customers" not in selected:
        if len(selected) < max_tables:
            selected.append("customers")

    if "regions" in selected and "customers" not in selected and len(selected) < max_tables:
        selected.append("customers")

    if "products" in selected and "orders" not in selected and any(
        phrase in q
        for phrase in (
            "selling",
            "sold",
            "sales",
            "revenue",
            "purchase",
            "purchases",
            "order",
            "orders",
        )
    ):
        if len(selected) < max_tables:
            selected.append("orders")


    # Product-revenue questions should use the product/order domain, not the
    # payments domain. "Revenue" by itself normally maps to payments, but when
    # the user explicitly asks which products generated revenue, orders is the
    # measure-bearing table.
    if "product" in q and "revenue" in q:
        selected = [
            table for table in selected
            if table not in {"payments", "refunds", "subscriptions"}
        ]

        if "products" not in selected:
            selected.insert(0, "products")

        if "orders" not in selected:
            selected.append("orders")

    return selected[:max_tables]


def _relationship_subset(selected_tables: list[str]) -> list[dict]:
    selected = set(selected_tables)
    return [
        rel
        for rel in RELATIONSHIPS
        if rel["left_table"] in selected and rel["right_table"] in selected
    ]


def build_schema_context(question: str, max_tables: int = 4) -> dict:
    selected_tables = select_relevant_tables(question, max_tables=max_tables)

    tables = {
        table_name: {
            "description": SCHEMA_CATALOG[table_name]["description"],
            "columns": SCHEMA_CATALOG[table_name]["columns"],
        }
        for table_name in selected_tables
    }

    relationships = _relationship_subset(selected_tables)

    if selected_tables:
        context_lines = [
            "APPROVED SCHEMA CONTEXT",
            "Only the following approved tables and columns may be used:",
        ]

        for table_name in selected_tables:
            metadata = SCHEMA_CATALOG[table_name]
            context_lines.append(f"\nTABLE: {table_name}")
            context_lines.append(f"BUSINESS MEANING: {metadata['description']}")
            context_lines.append("COLUMNS:")
            for column_name, meaning in metadata["columns"].items():
                context_lines.append(f"- {column_name}: {meaning}")

        if relationships:
            context_lines.append("\nAPPROVED RELATIONSHIPS:")
            for rel in relationships:
                context_lines.append(
                    f"- {rel['left_table']}.{rel['left_column']} = "
                    f"{rel['right_table']}.{rel['right_column']} "
                    f"({rel['meaning']})"
                )

        prompt_context = "\n".join(context_lines)
    else:
        prompt_context = (
            "NO APPROVED SCHEMA CONTEXT MATCHED. "
            "Do not generate SQL until the business question is clarified."
        )

    return {
        "question": question,
        "selected_tables": selected_tables,
        "tables": tables,
        "relationships": relationships,
        "prompt_context": prompt_context,
    }
