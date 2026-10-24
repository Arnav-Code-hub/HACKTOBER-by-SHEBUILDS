import subprocess
from unittest.mock import Mock

import pytest

from app import start


def test_production_start_migrates_before_one_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setattr(
        start.subprocess, "run", lambda command, **kwargs: calls.append((command, kwargs))
    )
    monkeypatch.setattr(start.os, "execv", lambda executable, command: calls.append((command, {})))
    start.main()
    assert calls[0][0][-3:] == ["alembic", "upgrade", "head"]
    assert calls[0][1]["check"] is True
    assert calls[1][0][-2:] == ["--workers", "1"]


def test_failed_migration_does_not_start_server(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        start.subprocess, "run", Mock(side_effect=subprocess.CalledProcessError(1, "alembic"))
    )
    execute = Mock()
    monkeypatch.setattr(start.os, "execv", execute)
    with pytest.raises(subprocess.CalledProcessError):
        start.main()
    execute.assert_not_called()
