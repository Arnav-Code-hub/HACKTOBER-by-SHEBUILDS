"""The health endpoint is the container's liveness probe — if it regresses,
every deploy hangs. Cheap test, high value."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
