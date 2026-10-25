"""HTTP surface for academics. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/academics", tags=["Academics"])

# TODO(academics): endpoints.
