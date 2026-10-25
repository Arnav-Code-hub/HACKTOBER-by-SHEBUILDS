"""Narrow media DTOs matching the existing web and Dart upload flow."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class UploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    filename: str = Field(min_length=1, max_length=255)
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    bytes: StrictInt = Field(gt=0, le=10485760)
    kind: Literal["report", "completion"]


class UploadAuthorization(BaseModel):
    upload_id: UUID
    upload_url: str
    parameters: dict[str, str]


class UploadComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    upload_id: UUID
    public_id: str = Field(min_length=1, max_length=255)
    version: StrictInt = Field(gt=0)
    signature: str = Field(pattern=r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")


class MediaRead(BaseModel):
    id: UUID
    url: str
    thumbnail_url: str


class VerifiedAsset(BaseModel):
    public_id: str
    asset_id: str
    version: int = Field(gt=0)
    resource_type: Literal["image"]
    type: Literal["upload"]
    format: Literal["jpg", "jpeg", "png", "webp"]
    bytes: int = Field(gt=0, le=10485760)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    created_at: datetime


class EvidencePhoto(BaseModel):
    """One photo as evidence: a signed detail URL and when it was uploaded."""

    id: UUID
    public_id: str
    version: int
    url: str
    uploaded_at: datetime
