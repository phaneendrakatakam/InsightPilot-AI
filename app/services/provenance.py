from __future__ import annotations

import hashlib
from typing import Any

from app.schemas.analytics import ProvenanceItem
from app.schemas.conversation import EvidenceSnapshot


def _fingerprint(sql: str | None) -> str | None:
    if not sql:
        return None
    normalized = " ".join(sql.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


def build_provenance(
    route: str,
    result: dict[str, Any],
    snapshot: EvidenceSnapshot | None = None,
) -> list[ProvenanceItem]:
    items: list[ProvenanceItem] = []

    if route == "v2_investigation":
        question = result.get("question") or ""
        steps = ((result.get("plan") or {}).get("steps") or [])
        for index, step in enumerate(steps, start=1):
            if step.get("status") != "completed":
                continue
            sql = step.get("sql")
            items.append(
                ProvenanceItem(
                    evidence_id=f"E{index}",
                    source_route="v2_investigation",
                    source_question=question,
                    tables=list(step.get("tables") or []),
                    row_count=int(step.get("row_count") or 0),
                    sql_fingerprint=_fingerprint(sql),
                    query_time_ms=step.get("execution_time_ms"),
                    grounding="executed_sql",
                )
            )
        return items

    if route == "v1_simple_query":
        evidence = result.get("evidence") or {}
        sql = result.get("sql")
        if result.get("status") == "answered":
            items.append(
                ProvenanceItem(
                    evidence_id="E1",
                    source_route="v1_simple_query",
                    source_question=result.get("question") or "",
                    tables=list(result.get("selected_tables") or []),
                    row_count=int(evidence.get("row_count") or 0),
                    sql_fingerprint=_fingerprint(sql),
                    query_time_ms=evidence.get("execution_time_ms"),
                    grounding="executed_sql",
                )
            )
        return items

    if route == "evidence_memory" and snapshot is not None:
        for evidence in snapshot.evidence:
            items.append(
                ProvenanceItem(
                    evidence_id=evidence.evidence_id,
                    source_route="evidence_memory",
                    source_question=snapshot.source_question,
                    tables=list(evidence.tables),
                    row_count=int(evidence.row_count or 0),
                    sql_fingerprint=_fingerprint(evidence.sql),
                    query_time_ms=evidence.execution_time_ms,
                    grounding="stored_evidence",
                )
            )

    return items
