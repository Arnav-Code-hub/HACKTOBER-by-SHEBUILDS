"""HTTP surface for audit. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/audit", tags=["Audit"])

# TODO(audit): endpoints.
