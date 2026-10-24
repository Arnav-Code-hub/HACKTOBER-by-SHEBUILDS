"""Persisted upload intents, provider verification and exclusive media attachment."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.core.roles import Role
from app.core.security import Principal
from app.integrations.cloudinary import MediaProvider
from app.modules.files.models import MediaAsset, UploadIntent
from app.modules.files.schemas import (
    MediaRead,
    UploadAuthorization,
    UploadComplete,
    UploadRequest,
    VerifiedAsset,
)


def _require_kind(principal: Principal, kind: str) -> None:
    if (kind == "report" and principal.role != Role.CITIZEN) or (
        kind == "completion" and principal.role != Role.OFFICER
    ):
        raise PermissionDeniedError("Your account cannot upload this kind of evidence.")


def _public_id(settings: Settings, owner: UUID, kind: str, upload_id: UUID) -> str:
    return f"{settings.cloudinary_folder}/users/{owner}/{kind}/{upload_id}"


def media_read(asset: MediaAsset, provider: MediaProvider) -> MediaRead:
    return MediaRead(
        id=asset.id,
        url=provider.delivery(asset.public_id, asset.version, thumbnail=False),
        thumbnail_url=provider.delivery(asset.public_id, asset.version, thumbnail=True),
    )


async def authorize_upload(
    session: AsyncSession,
    principal: Principal,
    body: UploadRequest,
    settings: Settings,
    provider: MediaProvider,
) -> UploadAuthorization:
    _require_kind(principal, body.kind)
    now, identity = datetime.now(UTC), uuid4()
    public_id = _public_id(settings, principal.user_id, body.kind, identity)
    url, parameters = provider.authorize(public_id, int(now.timestamp()))
    session.add(
        UploadIntent(
            id=identity,
            owner_id=principal.user_id,
            public_id=public_id,
            kind=body.kind,
            content_type=body.content_type,
            declared_bytes=body.bytes,
            created_at=now,
            expires_at=now + timedelta(seconds=settings.media_upload_ttl_seconds),
            is_demo=principal.is_demo,
        )
    )
    await session.flush()
    return UploadAuthorization(upload_id=identity, upload_url=url, parameters=parameters)


async def complete_upload(
    session: AsyncSession,
    principal: Principal,
    body: UploadComplete,
    settings: Settings,
    provider: MediaProvider,
) -> MediaRead:
    intent = await session.scalar(
        select(UploadIntent)
        .where(UploadIntent.id == body.upload_id, UploadIntent.owner_id == principal.user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if intent is None:
        raise NotFoundError("Upload authorization not found.")
    _require_kind(principal, intent.kind)
    expected = _public_id(settings, principal.user_id, intent.kind, intent.id)
    if body.public_id != intent.public_id or intent.public_id != expected:
        raise PermissionDeniedError("This photo does not belong to your upload authorization.")
    if not provider.verify_response(body.public_id, body.version, body.signature):
        raise ValidationError("The photo upload signature is invalid.")
    if intent.completed_asset_id is not None:
        asset = await session.get(MediaAsset, intent.completed_asset_id)
        if asset is None or asset.version != body.version:
            raise ConflictError("This upload was already completed with different evidence.")
        return media_read(asset, provider)
    now = datetime.now(UTC)
    raw = await provider.resource(intent.public_id)
    try:
        metadata = VerifiedAsset.model_validate(raw)
    except PydanticValidationError:
        raise ValidationError(
            "The uploaded file is not an allowed image of at most 10 MiB."
        ) from None
    if metadata.public_id != expected or metadata.version != body.version:
        raise ValidationError("The uploaded photo does not match the upload response.")
    # A photo uploaded before expiry remains completable after a lost response
    # or API outage. Expiry rejects late uploads, not retries of timely uploads.
    if metadata.created_at.tzinfo is not None and metadata.created_at > intent.expires_at:
        raise ConflictError("This upload authorization expired; request a new upload.")
    formats = {"image/jpeg": {"jpg", "jpeg"}, "image/png": {"png"}, "image/webp": {"webp"}}
    if (
        metadata.format not in formats[intent.content_type]
        or metadata.bytes != intent.declared_bytes
    ):
        raise ValidationError("The uploaded file does not match the selected image.")
    if (
        metadata.created_at.tzinfo is None
        or metadata.created_at < intent.created_at - timedelta(seconds=60)
        or metadata.created_at > now + timedelta(seconds=60)
    ):
        raise ValidationError("The uploaded photo has an unexpected upload date.")
    asset = MediaAsset(
        owner_id=principal.user_id,
        public_id=metadata.public_id,
        asset_id=metadata.asset_id,
        version=metadata.version,
        kind=intent.kind,
        format=metadata.format,
        bytes=metadata.bytes,
        width=metadata.width,
        height=metadata.height,
        uploaded_at=metadata.created_at,
        is_demo=principal.is_demo,
    )
    session.add(asset)
    await session.flush()
    intent.completed_asset_id = asset.id
    await session.flush()
    return media_read(asset, provider)


async def attach_report_media(
    session: AsyncSession,
    media_ids: list[UUID],
    owner_id: UUID,
    report_id: UUID,
) -> None:
    if not media_ids:
        return
    # Stable lock order prevents two submissions sharing several photos from
    # deadlocking. Locks also stop two different requests consuming one asset.
    assets = (
        await session.scalars(
            select(MediaAsset)
            .where(MediaAsset.id.in_(media_ids))
            .order_by(MediaAsset.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()
    if len(assets) != len(media_ids) or any(
        asset.owner_id != owner_id
        or asset.kind != "report"
        or asset.report_id is not None
        or asset.work_order_id is not None
        for asset in assets
    ):
        raise ValidationError("Choose your own unused report photos.")
    for asset in assets:
        asset.report_id = report_id
    await session.flush()


async def report_media(
    session: AsyncSession,
    report_ids: list[UUID],
    provider: MediaProvider,
) -> dict[UUID, list[MediaRead]]:
    if not report_ids:
        return {}
    assets = (
        await session.scalars(
            select(MediaAsset)
            .where(MediaAsset.report_id.in_(report_ids))
            .order_by(MediaAsset.uploaded_at, MediaAsset.id)
        )
    ).all()
    result: dict[UUID, list[MediaRead]] = {}
    for asset in assets:
        if asset.report_id is not None:
            result.setdefault(asset.report_id, []).append(media_read(asset, provider))
    return result
