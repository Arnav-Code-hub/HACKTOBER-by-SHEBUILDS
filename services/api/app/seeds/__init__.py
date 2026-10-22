"""Seed loader.

    make seed              reference + demo
    make seed-reference    reference only (production-safe)

The DATA lives in ``services/api/seeds/`` — deliberately outside the app package,
because it is content rather than code and is reviewed by different people.

reference/  real, committed, deterministic UUIDs. Idempotent, safe in production.
demo/       the SIH demonstration dataset. Every synthetic record carries a
            provenance label, matching the commitment in docs/SOURCES.md.
"""

from pathlib import Path

SEED_DIR = Path(__file__).resolve().parents[2] / "seeds"
REFERENCE_DIR = SEED_DIR / "reference"
DEMO_DIR = SEED_DIR / "demo"
