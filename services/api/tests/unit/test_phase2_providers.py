import asyncio
import threading
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.core.config import Settings, get_settings
from app.core.errors import ServiceUnavailableError
from app.integrations.cloudinary import CloudinaryMediaProvider
from app.integrations.firebase import FirebaseTokenVerifier, firebase_app


@pytest.fixture
def firebase_config(monkeypatch: pytest.MonkeyPatch):
    import firebase_admin
    from firebase_admin import auth

    monkeypatch.setenv("FIREBASE_PROJECT_ID", "test-project")
    get_settings.cache_clear()
    firebase_app.cache_clear()
    application = object()
    monkeypatch.setattr(firebase_admin, "get_app", lambda name: application)
    yield auth, application
    firebase_app.cache_clear()
    get_settings.cache_clear()


async def test_firebase_verifies_in_a_thread_with_revocation_check(
    firebase_config, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth, application = firebase_config
    event_loop_thread = threading.get_ident()
    calls = []

    def verify(token, **kwargs):
        calls.append((threading.get_ident(), token, kwargs))
        return {"uid": "firebase-uid", "role": "super_admin"}

    monkeypatch.setattr(auth, "verify_id_token", verify)
    assert await FirebaseTokenVerifier().verify("opaque-token") == "firebase-uid"
    assert calls[0][0] != event_loop_thread
    assert calls[0][2] == {"app": application, "check_revoked": True}


async def test_firebase_invalid_token_is_401_and_provider_failure_is_503(
    firebase_config, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth, _ = firebase_config
    monkeypatch.setattr(
        auth, "verify_id_token", Mock(side_effect=auth.InvalidIdTokenError("private-token"))
    )
    with pytest.raises(HTTPException) as error:
        await FirebaseTokenVerifier().verify("private-token")
    assert error.value.status_code == 401
    assert "private-token" not in error.value.detail
    monkeypatch.setattr(
        auth, "verify_id_token", Mock(side_effect=RuntimeError("private-credentials"))
    )
    with pytest.raises(ServiceUnavailableError) as error:
        await FirebaseTokenVerifier().verify("token")
    assert "private-credentials" not in str(error.value)


async def test_firebase_initializes_once_under_concurrent_requests(
    firebase_config, monkeypatch: pytest.MonkeyPatch
) -> None:
    import firebase_admin

    auth, application = firebase_config
    initialized = []

    def get_app(name):
        if not initialized:
            raise ValueError("not initialized")
        return application

    def initialize(*args, **kwargs):
        initialized.append(True)
        return application

    monkeypatch.setattr(firebase_admin, "get_app", get_app)
    monkeypatch.setattr(firebase_admin, "initialize_app", initialize)
    monkeypatch.setattr(auth, "verify_id_token", lambda *args, **kwargs: {"uid": "uid"})
    assert (
        await asyncio.gather(*[FirebaseTokenVerifier().verify("token") for _ in range(4)])
        == ["uid"] * 4
    )
    assert len(initialized) == 1


def test_cloudinary_signing_response_validation_and_bounded_delivery_urls() -> None:
    from cloudinary.utils import api_sign_request

    settings = Settings(
        _env_file=None,
        cloudinary_cloud_name="test-cloud",
        cloudinary_api_key="public-key",
        cloudinary_api_secret="server-secret",
        cloudinary_upload_preset="signed-demo",
    )
    provider = CloudinaryMediaProvider(settings)
    url, parameters = provider.authorize("janmaang/users/owner/report/asset", 1234)
    assert url == "https://api.cloudinary.com/v1_1/test-cloud/image/upload"
    signed = {
        key: value for key, value in parameters.items() if key not in {"signature", "api_key"}
    }
    assert parameters["signature"] == api_sign_request(signed, "server-secret", algorithm="sha256")
    assert parameters["allowed_formats"] == "jpg,jpeg,png,webp"
    assert parameters["overwrite"] == "false"
    assert "server-secret" not in str(parameters)
    signature = api_sign_request(
        {"public_id": "photo", "version": 123}, "server-secret", signature_version=1
    )
    assert provider.verify_response("photo", 123, signature)
    assert not provider.verify_response("different", 123, signature)
    for thumbnail, dimension in ((True, "320"), (False, "1280")):
        delivery = provider.delivery("photo", 123, thumbnail=thumbnail)
        assert delivery.startswith("https://res.cloudinary.com/test-cloud/image/upload/s--")
        assert f"w_{dimension}" in delivery and f"h_{dimension}" in delivery
        assert "c_limit" in delivery and "f_auto" in delivery and "q_auto" in delivery
        assert "server-secret" not in delivery


def test_unconfigured_cloudinary_fails_explicitly() -> None:
    with pytest.raises(ServiceUnavailableError):
        CloudinaryMediaProvider(Settings(_env_file=None)).authorize("asset", 123)
