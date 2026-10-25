"""HTTP surface for notifications. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# TODO(notifications): endpoints.
