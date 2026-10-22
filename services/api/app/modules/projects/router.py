"""HTTP surface for projects. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/projects", tags=["Projects"])

# TODO(projects): endpoints.
