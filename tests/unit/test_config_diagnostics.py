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


class TestFlagOnValidation:
    def on(self, **overrides: str) -> dict[str, str]:
        return environment(OPENMEDIA_DIAGNOSTIC_LOG="1", **overrides)

    def test_valid_settings_are_loaded(self) -> None:
        settings = Settings.from_env(self.on(OPENMEDIA_DIAGNOSTIC_LOG_DIR="/srv/om-logs",
            OPENMEDIA_DIAGNOSTIC_LOG_LEVEL="info"))
        assert settings.diagnostic_log_dir == Path("/srv/om-logs")
        assert settings.diagnostic_log_level == "INFO"

    @pytest.mark.parametrize("raw", ["logs", "./logs", "/var/log/om\x00x", ""])
    def test_directory_must_be_absolute_without_nul(self, raw: str) -> None:
        with pytest.raises(ConfigError, match="OPENMEDIA_DIAGNOSTIC_LOG_DIR must be an absolute path"):
            Settings.from_env(self.on(OPENMEDIA_DIAGNOSTIC_LOG_DIR=raw))

    @pytest.mark.parametrize("raw", ["/tmp/openmedia", "/tmp/openmedia/logs", "/tmp/openmedia/a/../logs"])
    def test_directory_must_be_outside_the_work_directory(self, raw: str) -> None:
        with pytest.raises(ConfigError, match="OPENMEDIA_DIAGNOSTIC_LOG_DIR must be outside OPENMEDIA_WORK_DIR"):
            Settings.from_env(self.on(OPENMEDIA_DIAGNOSTIC_LOG_DIR=raw))

    def test_a_sibling_with_a_shared_prefix_is_allowed(self) -> None:
        settings = Settings.from_env(self.on(OPENMEDIA_DIAGNOSTIC_LOG_DIR="/tmp/openmedia-logs"))
        assert settings.diagnostic_log_dir == Path("/tmp/openmedia-logs")

    @pytest.mark.parametrize("raw", ["TRACE", "verbose", "", "10"])
    def test_level_must_be_a_known_name(self, raw: str) -> None:
        with pytest.raises(ConfigError, match="OPENMEDIA_DIAGNOSTIC_LOG_LEVEL must be") as exc_info:
            Settings.from_env(self.on(OPENMEDIA_DIAGNOSTIC_LOG_LEVEL=raw))
        assert TOKEN not in str(exc_info.value)


def test_flag_off_ignores_directory_and_level() -> None:
    settings = Settings.from_env(environment(OPENMEDIA_DIAGNOSTIC_LOG="0",
        OPENMEDIA_DIAGNOSTIC_LOG_DIR="not/absolute", OPENMEDIA_DIAGNOSTIC_LOG_LEVEL="nonsense"))
    assert settings.diagnostic_log is False
    assert settings.diagnostic_log_dir == Path("/var/log/openmedia")
    assert settings.diagnostic_log_level == "DEBUG"
