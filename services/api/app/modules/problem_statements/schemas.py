"""Pydantic request/response models for problem statements.

Public: these are what generate the OpenAPI spec, and from it the
TypeScript client and Dart models in packages/contracts.
"""

from pydantic import BaseModel, ConfigDict


class ProblemStatementsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TODO(problem_statements): Create / Update / Read schemas.
