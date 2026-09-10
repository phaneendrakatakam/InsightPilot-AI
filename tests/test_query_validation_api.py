from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_validate_endpoint_accepts_safe_query():
    response = client.post(
        "/api/v1/query/validate",
        json={"sql": "SELECT customer_id FROM customers LIMIT 10"},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["valid"] is True
    assert body["tables"] == ["customers"]


def test_validate_endpoint_rejects_delete():
    response = client.post(
        "/api/v1/query/validate",
        json={"sql": "DELETE FROM customers WHERE customer_id = 1"},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["valid"] is False
