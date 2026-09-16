"""Process entry point for `python -m openmedia`.

Phase 1 fixes the command-line surface named by the runtime contract and quickstart so
later phases extend it rather than invent it. Startup, polling, configuration checking,
and health reporting are implemented in later phases; every mode therefore refuses with a
nonzero exit rather than reporting a success it cannot substantiate.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

_NOT_IMPLEMENTED = (
    "openmedia: the runtime is not implemented yet (specs/001-media-download/tasks.md "
    "Phase 1 establishes the package only)."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openmedia",
        description="Telegram bot delivering one public media link in a native upstream format.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check-config",
        action="store_true",
        help="Validate configuration and report redacted diagnostics, then exit.",
    )
    mode.add_argument(
        "--healthcheck",
        action="store_true",
        help="Report whether a running instance is healthy, then exit.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    print(_NOT_IMPLEMENTED, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
