"""HTTP surface for departments. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/departments", tags=["Departments"])

# TODO(departments): endpoints.
