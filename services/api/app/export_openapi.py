"""Export OpenAPI without requiring a running server or database connection."""

import json
from pathlib import Path

from app.main import create_app


def main() -> None:
    target = Path(__file__).resolve().parents[3] / "packages/contracts/openapi/openapi.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(create_app().openapi(), indent=2) + "\n", encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
