"""Run with python -m app.seeds; no live provider calls unless requested."""

import argparse
import asyncio
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import engine
from app.seeds.guard import SeedResetError, require_reset_allowed
from app.seeds.loader import reset_demo, seed, seed_counts
from app.seeds.media import CloudinarySeedProvider, seed_photos


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load clearly labelled JanMaang demonstration data."
    )
    parser.add_argument(
        "--reference",
        action="store_true",
        help="Reference only (no imported datasets yet; no writes).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear all application data in an explicitly allowlisted demo database.",
    )
    parser.add_argument(
        "--users-file", type=Path, help="One real Firebase UID per role; no passwords."
    )
    parser.add_argument(
        "--photos-manifest", type=Path, help="Approved packaged files or recorded Cloudinary IDs."
    )
    args = parser.parse_args()
    settings = get_settings()
    if args.reference:
        if args.reset or args.photos_manifest or args.users_file:
            parser.error("--reference cannot be combined with demo options")
        print("No reference dataset is imported; no database writes performed.")
        return
    if settings.is_production:
        parser.error("Demonstration seeding is disabled in production.")
    if args.reset:
        # Check before any database connection or provider side effect.
        require_reset_allowed(settings)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session, session.begin():
            # Serialize repeat seed/reset commands across processes.
            from sqlalchemy import text

            await session.execute(text("SELECT pg_advisory_xact_lock(17898701)"))
            if args.reset:
                await reset_demo(session, settings)
            await seed(session, users_path=args.users_file)
            if args.photos_manifest:
                await seed_photos(
                    session, settings, args.photos_manifest, CloudinarySeedProvider(settings)
                )
            counts = await seed_counts(session)
        print(
            f"Demo seed committed: {counts}. "
            "Firebase UIDs and approved photos require explicit configuration."
        )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except SeedResetError as exc:
        raise SystemExit(str(exc)) from None
    except Exception as exc:
        # Provider/DB exception text may contain a URL or credentials.
        raise SystemExit(
            f"Seed failed ({type(exc).__name__}); transaction rolled back. Check configuration."
        ) from None
