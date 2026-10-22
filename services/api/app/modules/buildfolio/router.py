"""HTTP surface for buildfolio. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/buildfolio", tags=["Buildfolio"])

# TODO(buildfolio): endpoints.
