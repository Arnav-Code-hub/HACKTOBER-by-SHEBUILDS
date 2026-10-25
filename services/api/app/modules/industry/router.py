"""HTTP surface for industry. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/industry", tags=["Industry"])

# TODO(industry): endpoints.
