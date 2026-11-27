"""The operator guide's credential-rotation block, run against stub host commands.

``deploy/README.md`` "Rotate the runtime credential" is executed verbatim by operators.
These tests extract that fenced block, point its fixed ``/opt/openmedia`` paths at a
temporary directory, and replace privileged and Docker commands with shell functions
that record their calls. They pin the order of side effects: the running service must
not be stopped, and the live token file must not be replaced, until the operator has
actually written a replacement.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

GUIDE = Path(__file__).resolve().parents[2] / "deploy" / "README.md"
LIVE_TOKEN = "live-token-before-rotation\n"
NEW_TOKEN = "replacement-token-from-editor"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


def _rotation_block() -> str:
    text = GUIDE.read_text(encoding="utf-8")
    section = text.split("### Rotate the runtime credential", 1)[1]
    match = re.search(r"```bash\n(.*?)```", section, re.DOTALL)
    assert match, "rotation block not found in deploy/README.md"
    return match.group(1)


# Stubs: `sudo` runs its command unprivileged (ownership changes are recorded, not
# applied); `sudoedit` writes $EDIT_CONTENT, or leaves the file untouched when it is
# unset, like an editor quit without saving. Guide functions only record their calls.
STUBS = r"""
calls=$ROOT/calls
sudo() {
  case "$1" in
    chown) echo "chown $2" >> "$calls" ;;
    # GNU `mv -T` (the guide's Linux hosts) has no BSD equivalent; the target is a file.
    mv) shift; args=(); for a; do [ "$a" = -fT ] && a=-f; args+=("$a"); done; mv "${args[@]}" ;;
    *) "$@" ;;
  esac
}
sudoedit() { [ -z "${EDIT_CONTENT+x}" ] || printf '%s\n' "$EDIT_CONTENT" > "$1"; }
confirm_selection() { echo confirm_selection >> "$calls"; }
stop_selected() { echo stop_selected >> "$calls"; }
start_checked() { echo start_checked >> "$calls"; }
dc() { echo "dc $*" >> "$calls"; }
ACTIVE_IMAGE=ghcr.io/example/openmedia@sha256:0000000000000000000000000000000000000000000000000000000000000000
"""


def _run(tmp_path: Path, edit_content: str | None) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    secrets = tmp_path / "opt" / "secrets"
    secrets.mkdir(parents=True)
    (secrets / "telegram_bot_token").write_text(LIVE_TOKEN, encoding="utf-8")
    block = _rotation_block().replace("/opt/openmedia", str(tmp_path / "opt"))
    env = {"PATH": "/usr/bin:/bin", "ROOT": str(tmp_path)}
    if edit_content is not None:
        env["EDIT_CONTENT"] = edit_content
    result = subprocess.run(
        ["bash", "-c", STUBS + block],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    calls_file = tmp_path / "calls"
    calls = calls_file.read_text(encoding="utf-8").splitlines() if calls_file.exists() else []
    return result, calls


def _leftovers(tmp_path: Path) -> list[Path]:
    return sorted((tmp_path / "opt" / "secrets").glob(".telegram_bot_token.*"))


def test_unsaved_or_empty_replacement_leaves_the_running_service_untouched(tmp_path: Path) -> None:
    result, calls = _run(tmp_path, edit_content=None)

    assert result.returncode != 0
    assert "stop_selected" not in calls
    assert (tmp_path / "opt" / "secrets" / "telegram_bot_token").read_text(encoding="utf-8") == LIVE_TOKEN
    assert _leftovers(tmp_path) == []
    assert "empty" in result.stderr.lower()


def test_written_replacement_stops_replaces_validates_and_starts_in_order(tmp_path: Path) -> None:
    result, calls = _run(tmp_path, edit_content=NEW_TOKEN)

    assert result.returncode == 0, result.stderr
    stop = calls.index("stop_selected")
    assert calls[0] == "confirm_selection"
    assert "chown root:10001" in calls[:stop]
    assert calls[stop + 1].startswith("dc ") and "--check-config" in calls[stop + 1]
    assert calls[stop + 2 :] == ["start_checked", "confirm_selection"]
    assert (tmp_path / "opt" / "secrets" / "telegram_bot_token").read_text(encoding="utf-8") == NEW_TOKEN + "\n"
    assert _leftovers(tmp_path) == []
