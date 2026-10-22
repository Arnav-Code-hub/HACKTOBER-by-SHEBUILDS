"""HTTP surface for impact. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/impact", tags=["Impact"])

# TODO(impact): endpoints.
