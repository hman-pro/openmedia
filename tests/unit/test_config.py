from __future__ import annotations

import pytest

from openmedia.config import ConfigError, Settings


TOKEN = "123456789:AA-this-value-must-never-be-rendered"


def environment(**overrides: str) -> dict[str, str]:
    values = {"TELEGRAM_BOT_TOKEN": TOKEN}
    values.update(overrides)
    return values


def test_token_is_required() -> None:
    with pytest.raises(ConfigError, match="TELEGRAM_BOT_TOKEN"):
        Settings.from_env({})


def test_token_is_redacted_from_objects_and_errors() -> None:
    settings = Settings.from_env(environment())
    assert TOKEN not in repr(settings)
    assert TOKEN not in str(settings)

    with pytest.raises(ConfigError) as exc_info:
        Settings.from_env(
            environment(OPENMEDIA_MAX_FILE_BYTES="not-an-integer")
        )
    assert TOKEN not in str(exc_info.value)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("OPENMEDIA_MAX_FILE_BYTES", "0"),
        ("OPENMEDIA_MAX_WORKERS", "-1"),
        ("OPENMEDIA_MAX_PENDING", "0"),
        ("OPENMEDIA_WORKSPACE_BYTES", "-1"),
    ],
)
def test_limits_must_be_positive(name: str, value: str) -> None:
    with pytest.raises(ConfigError, match=name):
        Settings.from_env(environment(**{name: value}))


def test_workspace_holds_at_least_two_outputs() -> None:
    with pytest.raises(ConfigError, match="OPENMEDIA_WORKSPACE_BYTES"):
        Settings.from_env(
            environment(
                OPENMEDIA_MAX_FILE_BYTES="50000000",
                OPENMEDIA_WORKSPACE_BYTES="99999999",
            )
        )


def test_log_level_is_validated() -> None:
    with pytest.raises(ConfigError, match="OPENMEDIA_LOG_LEVEL"):
        Settings.from_env(environment(OPENMEDIA_LOG_LEVEL="verbose"))


@pytest.mark.parametrize(
    "name",
    [
        "OPENMEDIA_INSPECTION_SECONDS",
        "OPENMEDIA_SELECTION_SECONDS",
        "OPENMEDIA_PROCESSING_SECONDS",
        "OPENMEDIA_CLEANUP_SECONDS",
    ],
)
def test_fixed_deadlines_cannot_be_overridden(name: str) -> None:
    with pytest.raises(ConfigError, match="fixed"):
        Settings.from_env(environment(**{name: "1"}))


def test_documented_defaults() -> None:
    settings = Settings.from_env(environment())
    assert settings.max_file_bytes == 50_000_000
    assert settings.max_workers == 2
    assert settings.max_pending == 100
    assert settings.workspace_bytes == 128 * 1024 * 1024
    assert settings.log_level == "INFO"
    assert settings.inspection_seconds == 60
    assert settings.selection_seconds == 900
    assert settings.processing_seconds == 600
    assert settings.cleanup_seconds == 900

