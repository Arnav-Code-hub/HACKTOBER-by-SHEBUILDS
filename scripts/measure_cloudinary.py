"""Run from services/api using its environment and Python dependencies."""

import argparse
import asyncio
import json
import ssl
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))

from app.core.config import get_settings
from app.integrations.cloudinary import CloudinaryMediaProvider
from app.integrations.measurement import BROWSER_ACCEPT, measure_asset


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure approved Cloudinary demonstration images."
    )
    parser.add_argument(
        "--public-id", required=True, action="append", help="Repeat for more assets"
    )
    parser.add_argument("--accept", default=BROWSER_ACCEPT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    settings = get_settings()
    provider = CloudinaryMediaProvider(settings)
    with httpx.Client(
        timeout=30, follow_redirects=False, verify=ssl.create_default_context()
    ) as client:
        results = [
            await measure_asset(
                provider, client, public_id, folder=settings.cloudinary_folder, accept=args.accept
            )
            for public_id in args.public_id
        ]
    result = {"measured_at": datetime.now(UTC).isoformat(), "assets": results}
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"Measured {len(results)} images; results saved to {args.output}.")
    else:
        print(text, end="")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        # SDK/HTTP exceptions can include credential-bearing provider URLs.
        print(
            "Measurement failed. Check Cloudinary configuration, approved asset IDs "
            "and delivery access.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
