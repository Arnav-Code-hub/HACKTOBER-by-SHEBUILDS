"""HTTP surface for auth. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["Auth"])

# TODO(auth): endpoints.
