from __future__ import annotations

from time import perf_counter

from app.schemas.analytics import TurnTraceSummary
from app.schemas.conversation import CopilotTurnResponse
from app.services.confidence_engine import assess_confidence
from app.services.evidence_memory import evidence_memory
from app.services.execution_router import execute_intent
from app.services.kpi_engine import build_kpis
from app.services.observability import (
    derive_query_metrics,
    new_trace_id,
    observability_store,
    utcnow,
)
from app.services.provenance import build_provenance
from app.services.session_store import session_store
from app.services.visualization_engine import build_charts


def _assistant_text(execution) -> str:
    if execution.route == "v2_investigation":
        return (
            execution.result.get("conclusion")
            or "The investigation completed without a conclusion."
        )

    return (
        execution.result.get("answer")
        or execution.result.get("message")
        or "The request completed."
    )


def run_copilot_turn(
    session_id: str,
    message: str,
) -> CopilotTurnResponse:
    trace_id = new_trace_id()
    started_at = utcnow()
    started_perf = perf_counter()
    accepted = None
    execution = None

    try:
        accepted = session_store.append_user_message(session_id, message)

        execution = execute_intent(
            session_id=session_id,
            message=message,
            intent=accepted.intent,
            context=accepted.context,
        )

        if execution.status == "completed":
            execution.kpis = build_kpis(
                route=execution.route,
                result=execution.result,
            )
            execution.charts = build_charts(
                route=execution.route,
                result=execution.result,
            )

        latest_snapshot = evidence_memory.latest(session_id)
        execution.provenance = build_provenance(
            route=execution.route,
            result=execution.result,
            snapshot=latest_snapshot,
        )
        execution.confidence = assess_confidence(
            message=message,
            intent=accepted.intent,
            execution=execution,
            provenance=execution.provenance,
        )

        if (
            latest_snapshot is not None
            and execution.route in {"v1_simple_query", "v2_investigation"}
        ):
            evidence_memory.enrich_latest(
                session_id=session_id,
                provenance=execution.provenance,
                confidence=execution.confidence,
                governance=execution.governance,
            )

        query_count, query_time_ms = derive_query_metrics(
            execution.route,
            execution.result,
        )
        duration_ms = round((perf_counter() - started_perf) * 1000, 2)

        trace = TurnTraceSummary(
            trace_id=trace_id,
            session_id=session_id,
            intent=accepted.intent.intent,
            route=execution.route,
            status=execution.status,
            started_at=started_at,
            duration_ms=duration_ms,
            query_count=query_count,
            query_time_ms=query_time_ms,
            evidence_count=len(execution.provenance),
            evidence_reused=execution.route == "evidence_memory",
            retry_count=0,
            governance_status=execution.governance.status,
        )
        execution.trace = trace
        observability_store.record(trace)

        assistant_message = session_store.append_assistant_message(
            session_id,
            _assistant_text(execution),
        )

        return CopilotTurnResponse(
            session_id=session_id,
            user_message=accepted.message,
            assistant_message=assistant_message,
            intent=accepted.intent,
            context=accepted.context,
            execution=execution,
        )

    except Exception as exc:
        duration_ms = round((perf_counter() - started_perf) * 1000, 2)

        trace = TurnTraceSummary(
            trace_id=trace_id,
            session_id=session_id,
            intent=(
                accepted.intent.intent
                if accepted is not None
                else "unresolved"
            ),
            route=(
                execution.route
                if execution is not None
                else "unresolved"
            ),
            status="failed",
            started_at=started_at,
            duration_ms=duration_ms,
            query_count=0,
            query_time_ms=0.0,
            evidence_count=0,
            evidence_reused=False,
            retry_count=0,
            governance_status=(
                execution.governance.status
                if execution is not None
                else "passed"
            ),
            error_class=exc.__class__.__name__,
        )
        observability_store.record(trace)
        raise
