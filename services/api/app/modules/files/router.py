"""HTTP surface for files. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/files", tags=["Files"])

# TODO(files): endpoints.
