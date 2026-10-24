"""Lazy, once-per-process Firebase Admin initialization and threaded verification."""

import asyncio
import json
from functools import lru_cache
from threading import Lock
from typing import Any, Protocol

from fastapi import HTTPException

from app.core.config import get_settings
from app.core.errors import ServiceUnavailableError

_initialization_lock = Lock()


class TokenVerifier(Protocol):
    async def verify(self, token: str) -> str: ...


@lru_cache
def firebase_app() -> Any:
    # lru_cache alone can execute a cache miss concurrently in multiple threads.
    with _initialization_lock:
        return _initialize_firebase()


def _initialize_firebase() -> Any:
    import firebase_admin
    from firebase_admin import credentials

    settings = get_settings()
    if not settings.firebase_project_id:
        raise ServiceUnavailableError("Firebase authentication is not configured.")
    try:
        credential = None
        if settings.firebase_credentials_json.get_secret_value():
            credential = credentials.Certificate(
                json.loads(settings.firebase_credentials_json.get_secret_value())
            )
        elif settings.firebase_credentials_path:
            credential = credentials.Certificate(settings.firebase_credentials_path)
        try:
            return firebase_admin.get_app("janmaang-api")
        except ValueError:
            return firebase_admin.initialize_app(
                credential,
                {"projectId": settings.firebase_project_id, "httpTimeout": 10},
                name="janmaang-api",
            )
    except Exception:
        raise ServiceUnavailableError(
            "Firebase authentication is not configured correctly."
        ) from None


class FirebaseTokenVerifier:
    async def verify(self, token: str) -> str:
        from firebase_admin import auth

        def verify_sync() -> str:
            application = firebase_app()
            try:
                claims = auth.verify_id_token(token, app=application, check_revoked=True)
            except (
                auth.InvalidIdTokenError,
                auth.ExpiredIdTokenError,
                auth.RevokedIdTokenError,
                auth.UserDisabledError,
                auth.UserNotFoundError,
                ValueError,
            ):
                raise HTTPException(
                    401,
                    "Invalid or expired authentication token.",
                    headers={"WWW-Authenticate": "Bearer"},
                ) from None
            except Exception:
                raise ServiceUnavailableError(
                    "Firebase verification is temporarily unavailable."
                ) from None
            uid = claims.get("uid")
            if not isinstance(uid, str) or not uid:
                raise HTTPException(401, "Invalid authentication token.")
            return uid

        return await asyncio.to_thread(verify_sync)
