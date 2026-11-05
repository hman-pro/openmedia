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



@pytest.mark.parametrize('direct,file', [('', ''), (TOKEN, ''), ('', '/secret'), (TOKEN, '/secret')])
def test_token_sources_conflict_before_read(monkeypatch, direct, file):
    monkeypatch.setattr('os.open', lambda *a, **k: pytest.fail('conflict must not read'))
    with pytest.raises(ConfigError, match='TELEGRAM_BOT_TOKEN.*TELEGRAM_BOT_TOKEN_FILE'):
        Settings.from_env({'TELEGRAM_BOT_TOKEN': direct, 'TELEGRAM_BOT_TOKEN_FILE': file})


def test_missing_token_names_both_alternatives():
    with pytest.raises(ConfigError, match='TELEGRAM_BOT_TOKEN.*TELEGRAM_BOT_TOKEN_FILE'):
        Settings.from_env({})


@pytest.mark.parametrize('token', ['legacy opaque value', 'x:y', TOKEN])
def test_legacy_direct_token_is_not_tightened(token):
    assert Settings.from_env({'TELEGRAM_BOT_TOKEN': token}).telegram_bot_token == token


@pytest.mark.parametrize('suffix', [b'', b'\n', b'\r\n'])
def test_file_token_newline_and_private_field(tmp_path, suffix):
    path = tmp_path / 'sentinel-secret-path'
    path.write_bytes(TOKEN.encode('ascii') + suffix)
    settings = Settings.from_env({'TELEGRAM_BOT_TOKEN_FILE': str(path)})
    assert settings.telegram_bot_token == TOKEN
    assert TOKEN not in repr(settings) and str(path) not in repr(settings)


@pytest.mark.parametrize('path', ['', 'relative', '/sentinel\x00secret'])
def test_file_token_path_rejected_safely(path):
    with pytest.raises(ConfigError, match='TELEGRAM_BOT_TOKEN_FILE: invalid path'):
        Settings.from_env({'TELEGRAM_BOT_TOKEN_FILE': path})


@pytest.mark.parametrize('content,category', [
    (b'', 'empty content'), (b'\n', 'empty content'), (b'\r\n', 'empty content'),
    (b'\xef\xbb\xbf123:x', 'invalid encoding'), (b'123:\xff', 'invalid encoding'),
    *[(value, 'invalid token shape') for value in [b' ', b'123:x\n\n', b'123:x\r',
        b'123:x\n456:y', b'123:x y', b'123:x\t', b'123:x\x00', b'123:x\x7f',
        b'abc:x', b':x', b'123:', b'123:x+', b' 123:x', b'123:x ']],
    (b'1:' + b'a' * 4095, 'oversized file'),
])
def test_file_token_parse_errors_are_safe(tmp_path, content, category):
    import traceback
    path = tmp_path / 'sentinel-malicious-path'
    path.write_bytes(content)
    with pytest.raises(ConfigError, match='TELEGRAM_BOT_TOKEN_FILE: ' + category) as caught:
        Settings.from_env({'TELEGRAM_BOT_TOKEN_FILE': str(path)})
    rendered = ''.join(traceback.format_exception(caught.value))
    assert str(path) not in rendered and 'sentinel-malicious-path' not in str(caught.value)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__


def test_file_token_maximum_size(tmp_path):
    path = tmp_path / 'token'
    path.write_bytes(b'1:' + b'a' * 4094)
    assert len(Settings.from_env({'TELEGRAM_BOT_TOKEN_FILE': str(path)}).telegram_bot_token) == 4096


def test_file_token_io_errors_suppress_raw_exception(monkeypatch):
    import traceback
    def denied(*args, **kwargs):
        raise PermissionError('sentinel-secret-os-error')
    monkeypatch.setattr('os.open', denied)
    values = {'TELEGRAM_BOT_TOKEN_FILE': '/sentinel-path'}
    with pytest.raises(ConfigError, match='unreadable file') as caught:
        Settings.from_env(values)
    assert 'sentinel' not in ''.join(traceback.format_exception(caught.value))


@pytest.mark.parametrize('kind', ['missing', 'directory', 'fifo'])
def test_file_token_missing_and_nonregular(tmp_path, monkeypatch, kind):
    import os
    path = tmp_path / 'token'
    if kind == 'directory':
        path.mkdir()
    elif kind == 'fifo':
        os.mkfifo(path)
        real_open = os.open
        def nonblocking_open(path, flags):
            assert flags & os.O_NONBLOCK, 'FIFO must never be opened in blocking mode'
            return real_open(path, flags)
        monkeypatch.setattr(os, 'open', nonblocking_open)
    with pytest.raises(ConfigError, match='unreadable file' if kind == 'missing' else 'nonregular file'):
        Settings.from_env({'TELEGRAM_BOT_TOKEN_FILE': str(path)})


def test_file_token_reads_bounded_nonblocking_and_always_closes(tmp_path, monkeypatch):
    import os
    path = tmp_path / 'token'
    path.write_bytes(b'123:abc')
    opened, reads, closed = [], [], []
    real_open, real_read, real_close = os.open, os.read, os.close
    def opening(path, flags):
        opened.append(flags)
        return real_open(path, flags)
    def reading(fd, count):
        reads.append(count)
        # Exercise short reads as well as the end-of-file path.
        return real_read(fd, min(count, 2))
    def closing(fd):
        closed.append(fd)
        return real_close(fd)
    monkeypatch.setattr(os, 'open', opening)
    monkeypatch.setattr(os, 'read', reading)
    monkeypatch.setattr(os, 'close', closing)
    assert Settings.from_env({'TELEGRAM_BOT_TOKEN_FILE': str(path)}).telegram_bot_token == '123:abc'
    assert opened[0] & os.O_NONBLOCK and opened[0] & os.O_ACCMODE == os.O_RDONLY
    assert max(reads) <= 4097 and len(closed) == 1


def test_unencodable_secret_path_has_safe_error():
    import traceback
    values = {'TELEGRAM_BOT_TOKEN_FILE': '/\ud800sentinel-private-path'}
    with pytest.raises(ConfigError, match='invalid path') as caught:
        Settings.from_env(values)
    assert 'sentinel-private-path' not in ''.join(traceback.format_exception(caught.value))


@pytest.mark.parametrize('operation', ['fstat', 'read'])
def test_file_token_descriptor_closed_after_io_failure(tmp_path, monkeypatch, operation):
    import os
    import traceback
    path = tmp_path / 'token'
    path.write_bytes(b'123:abc')
    closed = []
    close = os.close
    def closing(fd):
        closed.append(fd)
        close(fd)
    def failure(*args):
        raise OSError('sentinel-raw-secret-error')
    monkeypatch.setattr(os, 'close', closing)
    monkeypatch.setattr(os, operation, failure)
    with pytest.raises(ConfigError, match='unreadable file') as caught:
        Settings.from_env({'TELEGRAM_BOT_TOKEN_FILE': str(path)})
    assert len(closed) == 1
    assert 'sentinel-raw-secret-error' not in ''.join(traceback.format_exception(caught.value))


def test_oversized_secret_consumes_only_4097_bytes(tmp_path, monkeypatch):
    import os
    path = tmp_path / 'token'
    path.write_bytes(b'1:' + b'a' * 10000)
    read = os.read
    consumed = []
    def reading(fd, count):
        result = read(fd, min(count, 1000))
        consumed.append(len(result))
        return result
    monkeypatch.setattr(os, 'read', reading)
    with pytest.raises(ConfigError, match='oversized file'):
        Settings.from_env({'TELEGRAM_BOT_TOKEN_FILE': str(path)})
    assert sum(consumed) == 4097
