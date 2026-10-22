"""HTTP surface for users. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["Users"])

# TODO(users): endpoints.
