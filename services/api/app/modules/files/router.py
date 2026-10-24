"""The exact media paths already used by both frontend clients."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.integrations.cloudinary import MediaProvider, get_media_provider
from app.modules.files import service
from app.modules.files.schemas import MediaRead, UploadAuthorization, UploadComplete, UploadRequest

router = APIRouter(prefix="/media", tags=["Media"])


@router.post("/signature", response_model=UploadAuthorization)
async def signature(
    body: UploadRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
    settings: Settings = Depends(get_settings),
    provider: MediaProvider = Depends(get_media_provider),
) -> UploadAuthorization:
    return await service.authorize_upload(session, principal, body, settings, provider)


@router.post("/complete", response_model=MediaRead)
async def complete(
    body: UploadComplete,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
    settings: Settings = Depends(get_settings),
    provider: MediaProvider = Depends(get_media_provider),
) -> MediaRead:
    return await service.complete_upload(session, principal, body, settings, provider)
