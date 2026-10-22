"""HTTP surface for chat."""

from fastapi import APIRouter

router = APIRouter(prefix="/v1", tags=["chat"])

# TODO(chat): endpoints.
