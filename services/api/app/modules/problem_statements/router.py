"""HTTP surface for problem statements. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/problem-statements", tags=["Problem Statements"])

# TODO(problem_statements): endpoints.
