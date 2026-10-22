"""HTTP surface for deduplication."""

from fastapi import APIRouter

router = APIRouter(prefix="/v1", tags=["deduplication"])

# TODO(deduplication): endpoints.
