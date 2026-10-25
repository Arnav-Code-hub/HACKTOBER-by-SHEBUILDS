"""CSR pledges are records, never payment transactions."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class PledgeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount_paise: StrictInt = Field(gt=0, le=10**13)


class PledgeRead(BaseModel):
    id: UUID
    statement_id: UUID
    statement_title: str
    amount_paise: int
    status: Literal["pledged"]
    pledged_at: datetime


class PledgeList(BaseModel):
    items: list[PledgeRead]
