import httpx
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import ConflictError
from app.core.permissions import Permission, require
from app.core.roles import Role
from app.core.security import Principal
from app.main import create_app


def test_staging_starts_without_redis_and_health_is_public(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.delenv("REDIS_URL", raising=False)
    from app.core.config import get_settings

    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        response = client.get("/health")
        assert response.json() == {"status": "ok", "environment": "staging"}
    get_settings.cache_clear()


def test_cors_preflight_and_rejected_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:8080")
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Idempotency-Key,Content-Type",
        }
        response = client.options("/api/v1/reports", headers=headers)
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
        headers["Origin"] = "http://untrusted.test"
        assert client.options("/api/v1/reports", headers=headers).status_code == 400
        assert (
            client.get("/health", headers={"Origin": "http://localhost:3000"}).headers[
                "access-control-allow-origin"
            ]
            == "http://localhost:3000"
        )
    get_settings.cache_clear()


class ExampleBody(BaseModel):
    count: int


def test_public_error_format_does_not_echo_exception_or_invalid_input(app: FastAPI) -> None:
    @app.post("/_test/body")
    async def body(payload: ExampleBody) -> dict[str, int]:
        return {"count": payload.count}

    @app.get("/_test/conflict")
    async def conflict() -> None:
        raise ConflictError("The record changed.")

    @app.get("/_test/unexpected")
    async def unexpected() -> None:
        raise RuntimeError("secret-provider-key")

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.post("/_test/body", json={"count": "secret-input"}).json() == {
            "detail": "Check the submitted fields."
        }
        assert client.get("/_test/conflict").json() == {"detail": "The record changed."}
        response = client.get("/_test/unexpected")
        assert response.status_code == 500
        assert "secret-provider-key" not in response.text
        assert list(response.json()) == ["detail"]
        assert client.get("/missing").json() == {"detail": "Not Found"}


@pytest.mark.parametrize("principal", list(Role), indirect=True)
async def test_each_role_can_use_the_auth_fixture(
    app: FastAPI, authed_client: httpx.AsyncClient, principal: Principal
) -> None:
    @app.get("/_test/principal")
    async def current(p: Principal = Depends(require(Permission.PROBLEM_READ))) -> dict[str, str]:
        return {"role": p.role}

    response = await authed_client.get("/_test/principal")
    assert response.json() == {"role": principal.role}


async def test_missing_token_stays_unauthorized(app: FastAPI, client: httpx.AsyncClient) -> None:
    @app.get("/_test/protected")
    async def protected(p: Principal = Depends(require(Permission.PROBLEM_READ))) -> dict[str, str]:
        return {"role": p.role}

    response = await client.get("/_test/protected")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
