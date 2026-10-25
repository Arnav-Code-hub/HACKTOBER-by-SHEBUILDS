"""Lazy, once-per-process Firebase Admin initialization and threaded verification."""

import asyncio
import json
import time
from collections.abc import Callable
from functools import lru_cache
from threading import Lock
from typing import Any, NamedTuple, Protocol

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


class _AccountState(NamedTuple):
    checked_at: float
    disabled: bool
    tokens_valid_after: float  # seconds since the epoch; 0 if never revoked


def _unauthorized(detail: str = "Invalid or expired authentication token.") -> HTTPException:
    return HTTPException(401, detail, headers={"WWW-Authenticate": "Bearer"})


class FirebaseTokenVerifier:
    """Verifies the token signature on every request (locally, against cached
    Google certificates) and the account's disabled/revoked state at most once
    per ``revocation_ttl_seconds`` per user.

    `verify_id_token(check_revoked=True)` would call Firebase's admin API on
    every request. A disabled or revoked Firebase account therefore takes up
    to the TTL to be refused here; disabling the JanMaang profile in the
    database takes effect on the next request regardless.
    """

    def __init__(
        self,
        revocation_ttl_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = revocation_ttl_seconds
        self._clock = clock
        self._accounts: dict[str, _AccountState] = {}
        self._lock = Lock()

    def _account(self, auth: Any, application: Any, uid: str) -> _AccountState:
        now = self._clock()
        with self._lock:
            cached = self._accounts.get(uid)
        if cached is not None and now - cached.checked_at < self._ttl:
            return cached
        user = auth.get_user(uid, app=application)
        state = _AccountState(
            checked_at=now,
            disabled=bool(user.disabled),
            tokens_valid_after=(user.tokens_valid_after_timestamp or 0) / 1000,
        )
        with self._lock:
            self._accounts[uid] = state
        return state

    async def verify(self, token: str) -> str:
        from firebase_admin import auth

        def verify_sync() -> str:
            application = firebase_app()
            try:
                claims = auth.verify_id_token(token, app=application, check_revoked=False)
                uid = claims.get("uid")
                if not isinstance(uid, str) or not uid:
                    raise _unauthorized("Invalid authentication token.")
                account = self._account(auth, application, uid)
            except HTTPException:
                raise
            except (
                auth.InvalidIdTokenError,
                auth.ExpiredIdTokenError,
                auth.RevokedIdTokenError,
                auth.UserDisabledError,
                auth.UserNotFoundError,
                ValueError,
            ):
                raise _unauthorized() from None
            except Exception:
                raise ServiceUnavailableError(
                    "Firebase verification is temporarily unavailable."
                ) from None
            # Same rules as the SDK's check_revoked, from the cached account state.
            if account.disabled:
                raise _unauthorized("This account is disabled.")
            issued_at = claims.get("iat")
            if not isinstance(issued_at, (int, float)) or issued_at < account.tokens_valid_after:
                raise _unauthorized("This session was revoked. Sign in again.")
            return uid

        return await asyncio.to_thread(verify_sync)
