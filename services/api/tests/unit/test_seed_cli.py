import os
import subprocess
import sys

from tests.conftest import SERVICE_ROOT


def run_cli(*args: str, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "app.seeds", *args],
        cwd=SERVICE_ROOT,
        env={
            **os.environ,
            "DATABASE_URL": "postgresql+asyncpg://demo:never-print-this@unreachable.invalid:5432/demo",
            "ENVIRONMENT": "staging",
            "SEED_RESET_ALLOWED": "false",
            "SEED_RESET_TARGETS": "",
            **env,
        },
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def test_reference_cli_does_not_connect_to_a_database() -> None:
    result = run_cli("--reference")
    assert result.returncode == 0
    assert "no database writes" in result.stdout.lower()


def test_production_seed_refused_before_connection() -> None:
    result = run_cli(ENVIRONMENT="production")
    assert result.returncode != 0
    assert "disabled in production" in result.stderr
    assert "never-print-this" not in result.stderr


def test_reset_refused_before_connection_without_revealing_credentials() -> None:
    result = run_cli("--reset")
    assert result.returncode != 0
    assert "reset is disabled" in result.stderr
    assert "never-print-this" not in result.stderr
