"""Student submission and faculty review contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StrictInt, field_validator


class SubmissionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    team_id: UUID
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=5000)
    link: str | None = Field(default=None, max_length=2048)

    @field_validator("link")
    @classmethod
    def https_only(cls, value: str | None) -> str | None:
        if value is not None:
            if any(character.isspace() for character in value):
                raise ValueError("URL whitespace must be percent-encoded.")
            parsed = HttpUrl(value)
            if parsed.scheme != "https" or parsed.username or parsed.password:
                raise ValueError("Use a public HTTPS link without credentials.")
            # Persist the validated representation. HttpUrl accepts forms such
            # as HTTPS://host or https:host that the database's HTTPS guard
            # would reject if their original spelling were saved unchanged.
            normalized = str(parsed)
            if len(normalized) > 2048:
                raise ValueError("The normalized URL is too long.")
            return normalized
        return value


class ReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    score: StrictInt = Field(ge=1, le=5)
    comment: str = Field(min_length=1, max_length=2000)


class ReviewRead(BaseModel):
    score: int
    comment: str


class SubmissionRead(BaseModel):
    id: UUID
    team_id: UUID
    team_name: str
    statement_title: str
    title: str
    summary: str
    link: str | None
    submitted_at: datetime
    review_count: int
    my_review: ReviewRead | None


class SubmissionList(BaseModel):
    items: list[SubmissionRead]


class ReviewResult(BaseModel):
    id: UUID
