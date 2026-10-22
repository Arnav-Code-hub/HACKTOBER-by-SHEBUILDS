"""HTTP surface for analytics. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# TODO(analytics): endpoints.
