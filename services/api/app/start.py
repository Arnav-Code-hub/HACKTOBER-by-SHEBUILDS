"""Production entrypoint: migrate successfully, then run one API worker."""

import os
import subprocess
import sys

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    os.execv(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(settings.port),
            "--workers",
            "1",
        ],
    )


if __name__ == "__main__":
    main()
