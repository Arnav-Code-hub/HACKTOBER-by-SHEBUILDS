import json
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.modules.files.models import MediaAsset
from app.seeds.loader import seed
from app.seeds.media import seed_photos

pytestmark = pytest.mark.integration


class Provider:
    def __init__(self, **overrides: object) -> None:
        self.calls = 0
        self.overrides = overrides

    async def resolve(self, public_id: str, file: Path | None) -> dict[str, object]:
        self.calls += 1
        return {
            "public_id": public_id,
            "asset_id": f"test:{public_id}",
            "resource_type": "image",
            "type": "upload",
            "version": 123,
            "format": "jpg",
            "bytes": 12345,
            "width": 640,
            "height": 480,
            "created_at": "2026-10-21T10:00:00Z",
            **self.overrides,
        }


def manifest(tmp_path: Path, **overrides: object) -> Path:
    path = tmp_path / "photos.json"
    path.write_text(
        json.dumps(
            [
                {
                    "case": "reported",
                    "key": "before",
                    "source": "Test fixture only",
                    "approved_for_public_display": True,
                    "public_id": "janmaang/demo-seed/reported/before",
                    **overrides,
                }
            ]
        ),
        encoding="utf-8",
    )
    return path


async def test_recorded_photo_is_verified_and_reruns_do_not_attach_twice(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    await seed(db_session)
    provider, path = Provider(), manifest(tmp_path)
    settings = Settings(_env_file=None)
    await seed_photos(db_session, settings, path, provider)
    await seed_photos(db_session, settings, path, provider)
    assert provider.calls == 1
    asset = (await db_session.scalars(select(MediaAsset))).one()
    assert asset.public_id == "janmaang/demo-seed/reported/before"
    assert asset.bytes == 12345 and asset.is_demo


async def test_photo_limit_counts_previous_manifests(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    await seed(db_session)
    provider, settings = Provider(), Settings(_env_file=None)
    for number in range(3):
        path = manifest(
            tmp_path, key=f"photo{number}", public_id=f"janmaang/demo-seed/reported/photo{number}"
        )
        await seed_photos(db_session, settings, path, provider)
    path = manifest(tmp_path, key="fourth", public_id="janmaang/demo-seed/reported/fourth")
    with pytest.raises(ValueError, match="At most three"):
        await seed_photos(db_session, settings, path, provider)
    assert provider.calls == 3


@pytest.mark.parametrize(
    "overrides",
    [
        {"approved_for_public_display": False},
        {"public_id": "another-users-photo"},
        {"public_id": None, "file": "../../../../README.md"},
    ],
)
async def test_unapproved_or_outside_photo_references_never_reach_provider(
    db_session: AsyncSession,
    tmp_path: Path,
    overrides: dict[str, object],
) -> None:
    await seed(db_session)
    provider = Provider()
    with pytest.raises(ValueError):
        await seed_photos(
            db_session, Settings(_env_file=None), manifest(tmp_path, **overrides), provider
        )
    assert provider.calls == 0
    assert await db_session.scalar(select(func.count()).select_from(MediaAsset)) == 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"bytes": 10485761},
        {"format": "gif"},
        {"public_id": "wrong-id"},
        {"resource_type": "video"},
        {"type": "private"},
    ],
)
async def test_provider_metadata_is_checked_before_attach(
    db_session: AsyncSession,
    tmp_path: Path,
    overrides: dict[str, object],
) -> None:
    await seed(db_session)
    with pytest.raises(ValueError):
        await seed_photos(
            db_session, Settings(_env_file=None), manifest(tmp_path), Provider(**overrides)
        )
    assert await db_session.scalar(select(func.count()).select_from(MediaAsset)) == 0
