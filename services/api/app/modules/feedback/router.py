"""HTTP surface for feedback. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/feedback", tags=["Feedback"])

# TODO(feedback): endpoints.
