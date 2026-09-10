from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()

    assert body["app"] == "InsightPilot AI"
    assert body["status"] == "running"
    assert body["phase"] == "V1 — Data Assistant Foundation"
