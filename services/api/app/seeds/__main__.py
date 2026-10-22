"""Entrypoint for `python -m app.seeds`.

python -m app.seeds                reference + demo
python -m app.seeds --reference    reference only
"""

import argparse
import asyncio

from app.core.logging import configure_logging, get_logger
from app.seeds import DEMO_DIR, REFERENCE_DIR

logger = get_logger(__name__)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Load JanMaang seed data.")
    parser.add_argument(
        "--reference",
        action="store_true",
        help="Load reference data only — safe against a production database.",
    )
    args = parser.parse_args()

    configure_logging()
    logger.info("seed.start", reference_only=args.reference)

    # TODO(seeds): load REFERENCE_DIR/*.json, then DEMO_DIR/*.json unless --reference.
    # Reference rows use deterministic UUIDs so re-running is idempotent.
    logger.info("seed.dirs", reference=str(REFERENCE_DIR), demo=str(DEMO_DIR))
    logger.info("seed.done")


if __name__ == "__main__":
    asyncio.run(main())
