"""Read-only optional suggestions. Persistence is deliberately not a dependency."""

import asyncio
from time import monotonic
from typing import Any

from app.core.config import Settings
from app.core.errors import PermissionDeniedError, RateLimitError, ServiceUnavailableError
from app.core.logging import get_logger
from app.core.rate_limit import SuggestionRateLimiter
from app.core.roles import Role
from app.core.security import Principal
from app.integrations.gemini import SuggestionProvider
from app.modules.problems.schemas import ReportSuggestion, SuggestionRequest
from app.shared.categories import Category
from app.shared.enums import Language, Severity

logger = get_logger(__name__)
UNAVAILABLE = "Suggestions are unavailable right now. Enter the details yourself."


def _text(max_length: int) -> dict[str, Any]:
    return {"type": "string", "minLength": 1, "maxLength": max_length}


# Sent to Gemini instead of pydantic's schema: enums inline, no $ref/$defs or
# anyOf, which providers support unevenly. ReportSuggestion still validates the
# reply; a unit test keeps the two in step.
RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": [c.value for c in Category]},
        "severity": {"type": "string", "enum": [s.value for s in Severity]},
        "title": _text(120),
        "summary": _text(500),
        "mentioned_location": {"type": ["string", "null"], "maxLength": 200},
        "detected_language": {"type": "string", "enum": [lang.value for lang in Language]},
    },
    "required": [
        "category",
        "severity",
        "title",
        "summary",
        "mentioned_location",
        "detected_language",
    ],
    "additionalProperties": False,
}


async def suggest_report(
    principal: Principal,
    body: SuggestionRequest,
    settings: Settings,
    provider: SuggestionProvider,
    limiter: SuggestionRateLimiter,
) -> ReportSuggestion:
    started = monotonic()
    outcome = "unavailable"
    try:
        if principal.role != Role.CITIZEN:
            outcome = "forbidden"
            raise PermissionDeniedError("Only citizens can request report suggestions.")
        if (
            not settings.gemini_api_key.get_secret_value().strip()
            or not settings.gemini_model.strip()
        ):
            outcome = "not_configured"
            raise ServiceUnavailableError("Suggestions are not configured")
        try:
            limiter.check(principal.user_id)
        except RateLimitError:
            outcome = "rate_limited"
            raise
        try:
            raw = await asyncio.wait_for(
                provider.suggest(body.transcript, RESPONSE_SCHEMA),
                timeout=settings.gemini_timeout_seconds,
            )
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError("Missing structured output")
            suggestion = ReportSuggestion.model_validate_json(raw)
        except TimeoutError:
            outcome = "timeout"
            raise ServiceUnavailableError(UNAVAILABLE) from None
        except Exception:
            # Never forward SDK exceptions, model text or validation inputs.
            raise ServiceUnavailableError(UNAVAILABLE) from None
        outcome = "completed"
        return suggestion
    finally:
        logger.info(
            "report.suggestion",
            outcome=outcome,
            latency_ms=round((monotonic() - started) * 1000),
            user_id=str(principal.user_id),
        )
