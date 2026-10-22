"""HTTP surface for problems. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/problems", tags=["Problems"])

# TODO(problems): endpoints.
