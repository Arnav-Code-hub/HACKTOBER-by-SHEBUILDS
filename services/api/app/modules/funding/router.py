"""HTTP surface for funding. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/funding", tags=["Funding"])

# TODO(funding): endpoints.
