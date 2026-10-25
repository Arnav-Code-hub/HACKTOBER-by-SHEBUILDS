"""Cloudinary signing/delivery uses explicit options, never global SDK secrets."""

import asyncio
import hmac
import re
from datetime import UTC, datetime
from typing import Any, Protocol

from app.core.config import Settings, get_settings
from app.core.errors import ServiceUnavailableError, UpstreamError
from app.core.evidence import EvidenceCard


class MediaProvider(Protocol):
    def authorize(self, public_id: str, timestamp: int) -> tuple[str, dict[str, str]]: ...
    def verify_response(self, public_id: str, version: int, signature: str) -> bool: ...
    async def resource(self, public_id: str) -> dict[str, Any]: ...
    def delivery(self, public_id: str, version: int, *, thumbnail: bool) -> str: ...
    def panel(self, public_id: str, version: int) -> str: ...
    def evidence_card(self, card: EvidenceCard) -> str: ...


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

    def panel(self, public_id: str, version: int) -> str:
        """Equal 640x480 canvases preserve all evidence, without cropping."""
        from cloudinary.utils import cloudinary_url

        self._configured()
        url, _ = cloudinary_url(
            public_id,
            version=version,
            secure=True,
            sign_url=True,
            cloud_name=self.settings.cloudinary_cloud_name,
            api_secret=self.settings.cloudinary_api_secret.get_secret_value(),
            crop="pad",
            width=640,
            height=480,
            background="white",
            gravity="center",
            fetch_format="auto",
            quality="auto",
        )
        return str(url)

    def evidence_card(self, card: EvidenceCard) -> str:
        """Sign the entire composition, including saved evidence and verdict.

        Only application-generated immutable public IDs are accepted. Uploads
        use overwrite=false; replacing originals from the provider console is
        outside this evidence history contract. A shared URL is a snapshot,
        not a live status page and not a revocable authorization token.
        """
        from cloudinary.utils import cloudinary_url

        self._configured()
        for photo in (card.before, card.after):
            if photo is not None and (
                not re.fullmatch(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", photo.public_id)
                or photo.version < 1
                or photo.uploaded_at.utcoffset() is None
            ):
                raise ValueError("The evidence card requires saved image references and UTC dates.")

        # Each photo occupies a 640x480 panel below an 80px header. A final
        # pad adds an 80px footer; no fill/crop can conceal relevant damage.
        panel: dict[str, Any] = {
            "crop": "pad",
            "width": 640,
            "height": 480,
            "gravity": "center",
            "background": "white",
        }
        transformations: list[dict[str, Any]] = [
            panel,
            {
                "crop": "lpad",
                "width": 1280,
                "height": 560,
                "gravity": "south_west" if card.before else "south_east",
                "background": "white",
            },
            {
                "crop": "lpad",
                "width": 1280,
                "height": 640,
                "gravity": "north_west",
                "background": "white",
            },
        ]
        if card.before is not None:
            transformations.extend(
                [
                    {"overlay": {"public_id": card.after.public_id}},
                    panel,
                    {"flags": "layer_apply", "gravity": "north_west", "x": 640, "y": 80},
                ]
            )
        else:
            transformations.extend(_text_layer("No original photo attached", 24, 280, 22))

        def uploaded(photo_date: datetime) -> str:
            return photo_date.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")

        before_label = "Before"
        if card.before is not None:
            before_label += " - " + uploaded(card.before.uploaded_at)
        texts = [
            (f"Report {card.report_code}", 24, 14, 26),
            (before_label, 24, 54, 18),
            (f"After - round {card.after_round} - {uploaded(card.after.uploaded_at)}", 664, 54, 18),
            (card.verdict_label, 24, 576, 24),
            (
                "Evidence for human review; photos do not prove a repair. "
                "Status at card generation.",
                24,
                615,
                16,
            ),
        ]
        for text, x, y, size in texts:
            transformations.extend(_text_layer(text, x, y, size))
        transformations.append({"fetch_format": "auto", "quality": "auto"})
        base = card.before or card.after
        url, _ = cloudinary_url(
            base.public_id,
            version=base.version,
            secure=True,
            sign_url=True,
            cloud_name=self.settings.cloudinary_cloud_name,
            api_secret=self.settings.cloudinary_api_secret.get_secret_value(),
            transformation=transformations,
            long_url_signature=True,
        )
        return str(url)


def _text_layer(text: str, x: int, y: int, size: int) -> list[dict[str, Any]]:
    # Let the SDK escape text. Never interpolate raw text into URL components.
    return [
        {
            "overlay": {"font_family": "Arial", "font_size": size, "text": text},
            "color": "rgb:17212b",
        },
        {"flags": "layer_apply", "gravity": "north_west", "x": x, "y": y},
    ]


def get_media_provider() -> MediaProvider:
    return CloudinaryMediaProvider(get_settings())
