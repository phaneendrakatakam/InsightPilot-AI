from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.analytics import TurnTraceSummary
from app.services.runtime_store import RuntimeStore, runtime_store


def new_trace_id() -> str:
    return f"trc_{uuid4().hex}"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def derive_query_metrics(route: str, result: dict) -> tuple[int, float]:
    if route == "v1_simple_query":
        evidence = result.get("evidence") or {}
        query_count = 1 if result.get("sql") else 0
        return query_count, float(evidence.get("execution_time_ms") or 0.0)

    if route == "v2_investigation":
        count = 0
        elapsed = 0.0
        for step in ((result.get("plan") or {}).get("steps") or []):
            if step.get("status") != "completed" or not step.get("sql"):
                continue
            count += 1
            elapsed += float(step.get("execution_time_ms") or 0.0)
        return count, round(elapsed, 2)

    return 0, 0.0


class ObservabilityStore:
    def __init__(self, repository: RuntimeStore | None = None) -> None:
        self._repository = repository or runtime_store

    def record(self, trace: TurnTraceSummary) -> None:
        self._repository.save_trace(
            trace_id=trace.trace_id,
            session_id=trace.session_id,
            payload_json=trace.model_dump_json(),
            created_at=trace.started_at.isoformat(),
        )

    def recent(self, limit: int = 50) -> list[TurnTraceSummary]:
        return [
            TurnTraceSummary.model_validate_json(payload)
            for payload in self._repository.list_traces(limit=limit)
        ]

    def clear(self) -> None:
        self._repository.clear_traces()


observability_store = ObservabilityStore(repository=runtime_store)
