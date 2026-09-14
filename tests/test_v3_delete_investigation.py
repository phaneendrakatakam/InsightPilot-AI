from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.runtime_store import RuntimeStore
from app.services.session_store import SessionStore

client = TestClient(app)


def test_runtime_delete_removes_session_evidence_and_trace(tmp_path: Path):
    repo = RuntimeStore(tmp_path / "state.db")
    store = SessionStore(repo)

    session = store.create("Delete me")
    repo.save_evidence(
        "evs_delete",
        session.session_id,
        '{"snapshot_id":"evs_delete"}',
        "2026-09-14T00:00:00+00:00",
    )
    repo.save_trace(
        "trc_delete",
        session.session_id,
        '{"trace_id":"trc_delete"}',
        "2026-09-14T00:00:00+00:00",
    )

    store.delete(session.session_id)

    assert repo.get_session(session.session_id) is None
    assert repo.list_evidence(session.session_id) == []
    assert repo.list_traces(limit=50) == []


def test_delete_session_endpoint_returns_204_and_then_404():
    created = client.post("/api/v3/sessions", json={"title": "Delete endpoint"})
    assert created.status_code == 201
    session_id = created.json()["session_id"]

    deleted = client.delete(f"/api/v3/sessions/{session_id}")
    assert deleted.status_code == 204

    missing = client.get(f"/api/v3/sessions/{session_id}")
    assert missing.status_code == 404


def test_ui_has_delete_controls_for_recent_and_drawer():
    script = Path("app/static/js/insightpilot-v3.js").read_text(encoding="utf-8")

    assert "deleteInvestigation(session)" in script
    assert 'className = "recent-delete"' in script
    assert 'className = "drawer-delete"' in script
    assert 'method: "DELETE"' in script
