from __future__ import annotations

from pathlib import Path

import pytest

from openmedia.config import ConfigError, Settings


TOKEN = "123456789:AA-this-value-must-never-be-rendered"


def environment(**overrides: str) -> dict[str, str]:
    values = {"TELEGRAM_BOT_TOKEN": TOKEN}
    values.update(overrides)
    return values


def test_diagnostic_log_is_off_by_default() -> None:
    settings = Settings.from_env(environment())
    assert settings.diagnostic_log is False
    assert settings.diagnostic_log_dir == Path("/var/log/openmedia")
    assert settings.diagnostic_log_level == "DEBUG"


@pytest.mark.parametrize(("raw", "expected"), [("0", False), ("1", True)])
def test_flag_accepts_exactly_zero_or_one(raw: str, expected: bool) -> None:
    settings = Settings.from_env(environment(OPENMEDIA_DIAGNOSTIC_LOG=raw))
    assert settings.diagnostic_log is expected


@pytest.mark.parametrize("raw", ["true", "yes", "", " 1", "2", "on"])
def test_flag_rejects_everything_else(raw: str) -> None:
    with pytest.raises(ConfigError, match="OPENMEDIA_DIAGNOSTIC_LOG must be 0 or 1") as exc_info:
        Settings.from_env(environment(OPENMEDIA_DIAGNOSTIC_LOG=raw))
    assert TOKEN not in str(exc_info.value)
