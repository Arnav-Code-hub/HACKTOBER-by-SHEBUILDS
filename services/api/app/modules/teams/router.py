"""HTTP surface for teams. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/teams", tags=["Teams"])

# TODO(teams): endpoints.
