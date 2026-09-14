from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from app.core.governance import combine_governance_reports
from app.schemas.analytics import GovernanceReport
from app.schemas.conversation import EvidenceReference, EvidenceSnapshot
from app.services.runtime_store import RuntimeStore, runtime_store


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _snapshot_id() -> str:
    return f"evs_{uuid4().hex}"


class EvidenceMemory:
    """Persistent evidence memory for V3 conversational follow-ups."""

    def __init__(self, repository: RuntimeStore | None = None) -> None:
        self._repository = repository or runtime_store
        self._lock = RLock()

    def remember_v1(self, session_id: str, result: dict) -> EvidenceSnapshot | None:
        if result.get("status") != "answered":
            return None

        evidence_block = result.get("evidence") or {}
        governance = GovernanceReport.model_validate(
            result.get("governance") or {}
        )

        reference = EvidenceReference(
            evidence_id="E1",
            title="Query evidence",
            summary=result.get("answer") or "Grounded query result.",
            sql=result.get("sql"),
            tables=list(result.get("selected_tables") or []),
            rows=list(evidence_block.get("rows") or []),
            row_count=evidence_block.get("row_count"),
            execution_time_ms=evidence_block.get("execution_time_ms"),
            governance=governance,
        )

        snapshot = EvidenceSnapshot(
            snapshot_id=_snapshot_id(),
            session_id=session_id,
            source_route="v1_simple_query",
            source_question=result.get("question") or "",
            conclusion=result.get("answer"),
            caveats=[result["caveat"]] if result.get("caveat") else [],
            evidence=[reference],
            governance=governance,
            created_at=_utcnow(),
        )
        self._append(snapshot)
        return snapshot

    def remember_v2(self, session_id: str, result: dict) -> EvidenceSnapshot | None:
        if result.get("status") not in {"completed", "partial"}:
            return None

        steps = ((result.get("plan") or {}).get("steps") or [])
        references: list[EvidenceReference] = []
        governance_reports: list[GovernanceReport | dict | None] = []

        for index, step in enumerate(steps, start=1):
            if step.get("status") != "completed":
                continue

            step_governance = (
                GovernanceReport.model_validate(step["governance"])
                if step.get("governance")
                else None
            )
            governance_reports.append(step_governance)

            references.append(
                EvidenceReference(
                    evidence_id=f"E{index}",
                    title=step.get("title") or f"Evidence {index}",
                    summary=step.get("evidence_summary") or "",
                    sql=step.get("sql"),
                    tables=list(step.get("tables") or []),
                    rows=list(step.get("rows") or []),
                    row_count=step.get("row_count"),
                    execution_time_ms=step.get("execution_time_ms"),
                    governance=step_governance,
                )
            )

        governance = combine_governance_reports(*governance_reports)

        snapshot = EvidenceSnapshot(
            snapshot_id=_snapshot_id(),
            session_id=session_id,
            source_route="v2_investigation",
            source_question=result.get("question") or "",
            conclusion=result.get("conclusion"),
            caveats=list(result.get("caveats") or []),
            evidence=references,
            governance=governance,
            created_at=_utcnow(),
        )
        self._append(snapshot)
        return snapshot

    def latest(self, session_id: str) -> EvidenceSnapshot | None:
        items = self.list_for_session(session_id)
        return items[-1] if items else None

    def list_for_session(self, session_id: str) -> list[EvidenceSnapshot]:
        with self._lock:
            payloads = self._repository.list_evidence(session_id)
            return [
                EvidenceSnapshot.model_validate_json(payload)
                for payload in payloads
            ]

    def find_relevant(
        self,
        session_id: str,
        keywords: list[str],
    ) -> list[EvidenceReference]:
        snapshot = self.latest(session_id)
        if snapshot is None:
            return []

        normalized = [item.lower().strip() for item in keywords if item.strip()]
        if not normalized:
            return []

        matches: list[EvidenceReference] = []
        for evidence in snapshot.evidence:
            haystack = f"{evidence.title} {evidence.summary}".lower()
            if any(keyword in haystack for keyword in normalized):
                matches.append(evidence.model_copy(deep=True))
        return matches

    def enrich_latest(
        self,
        session_id: str,
        provenance,
        confidence,
        governance: GovernanceReport,
    ) -> EvidenceSnapshot | None:
        with self._lock:
            snapshots = self.list_for_session(session_id)
            if not snapshots:
                return None

            snapshot = snapshots[-1]
            snapshot.provenance = list(provenance)
            snapshot.confidence = confidence
            snapshot.governance = governance
            self._repository.save_evidence(
                snapshot_id=snapshot.snapshot_id,
                session_id=snapshot.session_id,
                payload_json=snapshot.model_dump_json(),
                created_at=snapshot.created_at.isoformat(),
            )
            return snapshot.model_copy(deep=True)

    def clear(self) -> None:
        with self._lock:
            self._repository.clear_evidence()

    def _append(self, snapshot: EvidenceSnapshot) -> None:
        with self._lock:
            self._repository.save_evidence(
                snapshot_id=snapshot.snapshot_id,
                session_id=snapshot.session_id,
                payload_json=snapshot.model_dump_json(),
                created_at=snapshot.created_at.isoformat(),
            )


evidence_memory = EvidenceMemory(repository=runtime_store)
