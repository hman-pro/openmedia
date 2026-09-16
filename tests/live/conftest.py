"""Opt-in live source checks.

Everything here reaches a real upstream, so the suite is excluded by default and each test
must carry ``@pytest.mark.live``. Real example URLs age, identify real accounts, and depend
on network location, so they live in a machine-local manifest named by
``OPENMEDIA_LIVE_MANIFEST`` rather than in the repository. A missing manifest skips with a
reason; per the quickstart, it must never read as a pass.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

MANIFEST_ENV_VAR = "OPENMEDIA_LIVE_MANIFEST"
EXAMPLE_MANIFEST = Path(__file__).parent.parent / "fixtures" / "live-sources.example.json"


@pytest.fixture(scope="session")
def live_manifest() -> list[dict[str, Any]]:
    """Load the machine-local live source manifest, or skip with an actionable reason."""
    location = os.environ.get(MANIFEST_ENV_VAR)
    if not location:
        pytest.skip(
            f"{MANIFEST_ENV_VAR} is not set. Copy {EXAMPLE_MANIFEST} outside version "
            "control, fill in credential-free public examples, and point the variable at it."
        )

    path = Path(location)
    if not path.is_file():
        pytest.skip(f"{MANIFEST_ENV_VAR} points at {path}, which does not exist.")

    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    if not cases:
        pytest.skip(f"{path} contains no cases.")
    return cases
