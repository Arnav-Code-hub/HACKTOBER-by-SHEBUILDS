"""Cloudinary signing/delivery uses explicit options, never global SDK secrets."""

import asyncio
import hmac
import re
from typing import Any, Protocol

from app.core.config import Settings, get_settings
from app.core.errors import ServiceUnavailableError, UpstreamError


class MediaProvider(Protocol):
    def authorize(self, public_id: str, timestamp: int) -> tuple[str, dict[str, str]]: ...
    def verify_response(self, public_id: str, version: int, signature: str) -> bool: ...
    async def resource(self, public_id: str) -> dict[str, Any]: ...
    def delivery(self, public_id: str, version: int, *, thumbnail: bool) -> str: ...


class CloudinaryMediaProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _configured(self) -> None:
        if not (
            re.fullmatch(r"[A-Za-z0-9_-]+", self.settings.cloudinary_cloud_name)
            and self.settings.cloudinary_api_key
            and self.settings.cloudinary_api_secret.get_secret_value()
        ):
            raise ServiceUnavailableError("Cloudinary media is not configured.")

    def authorize(self, public_id: str, timestamp: int) -> tuple[str, dict[str, str]]:
        from cloudinary.utils import api_sign_request

        self._configured()
        if not self.settings.cloudinary_upload_preset:
            raise ServiceUnavailableError("A signed Cloudinary upload preset is required.")
        parameters = {
            "timestamp": str(timestamp),
            "public_id": public_id,
            "overwrite": "false",
            "allowed_formats": "jpg,jpeg,png,webp",
            "type": "upload",
            "upload_preset": self.settings.cloudinary_upload_preset,
        }
        parameters["signature"] = api_sign_request(
            parameters, self.settings.cloudinary_api_secret.get_secret_value(), algorithm="sha256"
        )
        parameters["api_key"] = self.settings.cloudinary_api_key
        return (
            f"https://api.cloudinary.com/v1_1/{self.settings.cloudinary_cloud_name}/image/upload",
            parameters,
        )

    def verify_response(self, public_id: str, version: int, signature: str) -> bool:
        from cloudinary.utils import api_sign_request

        self._configured()
        # Response signatures use the v1 public_id/version payload even with
        # newer upload signing. Support the provider's SHA-1 and SHA-256 modes.
        return any(
            hmac.compare_digest(
                signature,
                api_sign_request(
                    {"public_id": public_id, "version": version},
                    self.settings.cloudinary_api_secret.get_secret_value(),
                    algorithm=algorithm,
                    signature_version=1,
                ),
            )
            for algorithm in ("sha1", "sha256")
        )

    async def resource(self, public_id: str) -> dict[str, Any]:
        import cloudinary.api
        import cloudinary.exceptions

        self._configured()
        try:
            result = await asyncio.to_thread(
                cloudinary.api.resource,
                public_id,
                resource_type="image",
                type="upload",
                cloud_name=self.settings.cloudinary_cloud_name,
                api_key=self.settings.cloudinary_api_key,
                api_secret=self.settings.cloudinary_api_secret.get_secret_value(),
                timeout=15,
            )
            return dict(result)
        except cloudinary.exceptions.NotFound:
            raise UpstreamError(
                "The photo is not available yet; retry upload completion."
            ) from None
        except Exception:
            raise UpstreamError("Cloudinary could not verify the photo; retry shortly.") from None

    def delivery(self, public_id: str, version: int, *, thumbnail: bool) -> str:
        from cloudinary.utils import cloudinary_url

        self._configured()
        url, _ = cloudinary_url(
            public_id,
            version=version,
            secure=True,
            sign_url=True,
            cloud_name=self.settings.cloudinary_cloud_name,
            api_secret=self.settings.cloudinary_api_secret.get_secret_value(),
            crop="limit",
            width=320 if thumbnail else 1280,
            height=320 if thumbnail else 1280,
            fetch_format="auto",
            quality="auto",
        )
        return str(url)


def get_media_provider() -> MediaProvider:
    return CloudinaryMediaProvider(get_settings())
