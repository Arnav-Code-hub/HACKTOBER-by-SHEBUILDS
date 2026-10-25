"""HTTP surface for maps. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/maps", tags=["Maps"])

# TODO(maps): endpoints.
