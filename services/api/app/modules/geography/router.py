"""HTTP surface for geography. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/geography", tags=["Geography"])

# TODO(geography): endpoints.
