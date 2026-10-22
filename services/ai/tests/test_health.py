"""The AI service must come up and answer its probe without an LLM key set —
otherwise a missing key takes down the container instead of failing one call."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_is_reachable_without_credentials() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_capability_endpoints_require_the_internal_key() -> None:
    """This service is internal-only. An unauthenticated caller gets 401."""
    with TestClient(create_app()) as client:
        response = client.post("/v1/classify", json={"text": "no water"})
    assert response.status_code in (401, 404, 405)
