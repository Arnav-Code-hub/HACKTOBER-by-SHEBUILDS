"""Approved seed photos only; metadata comes from Cloudinary, not a JSON URL."""

import asyncio
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.roles import Role
from app.modules.files.models import MediaAsset
from app.modules.problems.models import Report
from app.seeds import DEMO_DIR
from app.seeds.data import seed_id, user_id


class PhotoEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case: Literal["reported", "prioritised", "in_progress"]
    key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    approved_for_public_display: Literal[True]
    source: str = Field(min_length=1)
    file: str | None = None
    public_id: str | None = None

    @model_validator(mode="after")
    def one_source(self) -> "PhotoEntry":
        if (self.file is None) == (self.public_id is None):
            raise ValueError("Supply one packaged file or one recorded public_id")
        return self


class AssetMetadata(BaseModel):
    # Cloudinary includes additional fields; keep only authoritative metadata.
    public_id: str
    asset_id: str
    resource_type: Literal["image"]
    type: Literal["upload"]
    version: int = Field(gt=0)
    format: Literal["jpg", "jpeg", "png", "webp"]
    bytes: int = Field(gt=0, le=10485760)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    created_at: datetime


class SeedMediaProvider(Protocol):
    async def resolve(self, public_id: str, file: Path | None) -> dict[str, Any]: ...


class CloudinarySeedProvider:
    def __init__(self, settings: Settings) -> None:
        if not all(
            (
                settings.cloudinary_cloud_name,
                settings.cloudinary_api_key,
                settings.cloudinary_api_secret.get_secret_value(),
            )
        ):
            raise ValueError("Cloudinary credentials are required to seed photos.")
        self.options = {
            "cloud_name": settings.cloudinary_cloud_name,
            "api_key": settings.cloudinary_api_key,
            "api_secret": settings.cloudinary_api_secret.get_secret_value(),
            "timeout": 20,
        }

    async def resolve(self, public_id: str, file: Path | None) -> dict[str, Any]:
        import cloudinary.api
        import cloudinary.exceptions
        import cloudinary.uploader

        def resolve_sync() -> dict[str, Any]:
            try:
                return dict(
                    cloudinary.api.resource(public_id, resource_type="image", **self.options)
                )
            except cloudinary.exceptions.NotFound:
                if file is None:
                    raise ValueError(
                        "A recorded seed photo is not present in Cloudinary."
                    ) from None
            cloudinary.uploader.upload(
                str(file),
                public_id=public_id,
                overwrite=False,
                resource_type="image",
                allowed_formats=["jpg", "jpeg", "png", "webp"],
                **self.options,
            )
            return dict(cloudinary.api.resource(public_id, resource_type="image", **self.options))

        return await asyncio.to_thread(resolve_sync)


async def seed_photos(
    session: AsyncSession,
    settings: Settings,
    manifest: Path,
    provider: SeedMediaProvider,
) -> None:
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Photo manifest must be a list.")
    entries = [PhotoEntry.model_validate(value) for value in raw]
    if any(count > 3 for count in Counter(entry.case for entry in entries).values()):
        raise ValueError("At most three seed photos per report.")
    if len({(entry.case, entry.key) for entry in entries}) != len(entries):
        raise ValueError("Seed photo keys must be unique within each case.")
    photo_root = (DEMO_DIR / "photos").resolve()
    for entry in entries:
        identity = seed_id(f"photo/{entry.case}/{entry.key}")
        if await session.get(MediaAsset, identity) is not None:
            continue
        # Include photos from previous manifests, not only this file's count.
        # The report lock also serializes direct callers outside the seed CLI.
        report = await session.scalar(
            select(Report).where(Report.id == seed_id(f"report/{entry.case}")).with_for_update()
        )
        if report is None:
            raise ValueError("Seed the demonstration reports before their photos.")
        count = await session.scalar(
            select(func.count()).select_from(MediaAsset).where(MediaAsset.report_id == report.id)
        )
        if count is not None and count >= 3:
            raise ValueError("At most three seed photos per report.")
        expected = f"{settings.cloudinary_folder}/demo-seed/{entry.case}/{entry.key}"
        if entry.public_id is not None and entry.public_id != expected:
            raise ValueError("Recorded seed public_id must match its deterministic demo-seed path.")
        file = None
        if entry.file is not None:
            file = (photo_root / entry.file).resolve()
            if not file.is_relative_to(photo_root) or not file.is_file():
                raise ValueError("Seed photo must be a packaged file inside demo/photos.")
            if (
                file.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}
                or not 0 < file.stat().st_size <= 10485760
            ):
                raise ValueError("Seed photos must be JPEG, PNG or WebP, at most 10 MiB.")
        metadata = AssetMetadata.model_validate(await provider.resolve(expected, file))
        if metadata.public_id != expected or metadata.created_at.tzinfo is None:
            raise ValueError("Cloudinary returned unexpected seed asset identity or timestamp.")
        session.add(
            MediaAsset(
                id=identity,
                owner_id=user_id(Role.CITIZEN),
                report_id=seed_id(f"report/{entry.case}"),
                kind="report",
                public_id=metadata.public_id,
                asset_id=metadata.asset_id,
                version=metadata.version,
                format=metadata.format,
                bytes=metadata.bytes,
                width=metadata.width,
                height=metadata.height,
                uploaded_at=metadata.created_at,
                is_demo=True,
            )
        )
        await session.flush()
