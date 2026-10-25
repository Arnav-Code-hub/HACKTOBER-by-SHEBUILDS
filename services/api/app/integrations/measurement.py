"""Measure actual delivered image bodies. No estimated savings or sample results."""

from typing import Any
from urllib.parse import urlsplit

import httpx

from app.integrations.cloudinary import MediaProvider
from app.modules.files.schemas import VerifiedAsset

BROWSER_ACCEPT = "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
MAX_BYTES = 10485760


def measure_body(client: httpx.Client, url: str, *, accept: str) -> tuple[int, str]:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "res.cloudinary.com":
        raise ValueError("Measurement requires a server-generated Cloudinary HTTPS URL.")
    with client.stream(
        "GET", url, headers={"Accept": accept, "Accept-Encoding": "identity"}
    ) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").split(";", 1)[0]
        if not content_type.startswith("image/"):
            raise ValueError("Cloudinary did not return an image.")
        size = 0
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError("The measured image exceeds the 10 MiB demonstration limit.")
    if not size:
        raise ValueError("Cloudinary returned an empty image.")
    return size, content_type


async def measure_asset(
    provider: MediaProvider,
    client: httpx.Client,
    public_id: str,
    *,
    folder: str,
    accept: str = BROWSER_ACCEPT,
) -> dict[str, Any]:
    if not public_id.startswith(folder + "/"):
        raise ValueError("Measure only approved assets in the configured application folder.")
    asset = VerifiedAsset.model_validate(await provider.resource(public_id))
    if asset.public_id != public_id:
        raise ValueError("The provider returned a different asset.")
    measurements = []
    for variant, url in (
        ("thumbnail", provider.delivery(public_id, asset.version, thumbnail=True)),
        ("detail", provider.delivery(public_id, asset.version, thumbnail=False)),
        ("comparison_panel", provider.panel(public_id, asset.version)),
    ):
        delivered, content_type = measure_body(client, url, accept=accept)
        measurements.append(
            {
                "variant": variant,
                "delivered_bytes": delivered,
                "content_type": content_type,
                "saved_bytes": asset.bytes - delivered,
                "savings_percent": (asset.bytes - delivered) / asset.bytes * 100,
            }
        )
    return {
        "public_id": public_id,
        "version": asset.version,
        "original_bytes": asset.bytes,
        "original_bytes_source": "Cloudinary Admin metadata",
        "accept": accept,
        "measurement": "Actual response body bytes; excludes HTTP headers and TLS overhead.",
        "variants": measurements,
    }
