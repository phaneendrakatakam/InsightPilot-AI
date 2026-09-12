from fastapi.testclient import TestClient

import app.api.routes.investigate as investigate_route
from app.main import app
from app.schemas.investigation import (
    InvestigationFinding,
    InvestigationPlan,
    InvestigationResponse,
    InvestigationStep,
)
from app.services.gemini_service import GeminiServiceError
from app.services.investigation_planner import InvestigationPlannerError

client = TestClient(app)


def _completed_response(question: str) -> InvestigationResponse:
    return InvestigationResponse(
        question=question,
        status="completed",
        plan=InvestigationPlan(
            question=question,
            investigation_goal="Identify evidence-backed drivers.",
            steps=[
                InvestigationStep(
                    step_id="step_1",
                    title="Revenue comparison",
                    objective="Compare successful payment revenue in July and August.",
                    status="completed",
                    tables=["payments"],
                    row_count=2,
                    rows=[
                        {"month": "July", "revenue": 1902744},
                        {"month": "August", "revenue": 1770795},
                    ],
                    evidence_summary="Revenue declined in August.",
                )
            ],
        ),
        findings=[
            InvestigationFinding(
                title="Revenue decline",
                evidence="Revenue declined from July to August.",
                significance="high",
            )
        ],
        conclusion="Successful payment revenue declined in August.",
        caveats=[],
    )


def test_investigate_endpoint_returns_v2_report(monkeypatch):
    monkeypatch.setattr(
        investigate_route,
        "investigate",
        lambda question: _completed_response(question),
    )

    response = client.post(
        "/api/v2/investigate",
        json={"question": "Why did revenue decline in August compared with July?"},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "completed"
    assert body["question"] == "Why did revenue decline in August compared with July?"
    assert body["findings"][0]["significance"] == "high"
    assert body["plan"]["steps"][0]["status"] == "completed"


def test_investigate_endpoint_maps_planner_error_to_422(monkeypatch):
    def fake_investigate(question: str):
        raise InvestigationPlannerError("Investigation question cannot be empty.")

    monkeypatch.setattr(investigate_route, "investigate", fake_investigate)

    response = client.post(
        "/api/v2/investigate",
        json={"question": " "},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Investigation question cannot be empty."


def test_investigate_endpoint_maps_gemini_error_to_502(monkeypatch):
    def fake_investigate(question: str):
        raise GeminiServiceError("Gemini investigation request failed.")

    monkeypatch.setattr(investigate_route, "investigate", fake_investigate)

    response = client.post(
        "/api/v2/investigate",
        json={"question": "Why did revenue decline?"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Gemini investigation request failed."
