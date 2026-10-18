# Media Delivery Titles Validation

This record distinguishes executed controlled checks from packaging and external
acceptance checks. No live Telegram, source, push, or deployment operation is
authorized by this record.

## T001 — Baseline (2026-10-18)

- Starting commit: `47010ca8ee88761cc0aebf83fa20366cc4d756fb`
  (`feat(dock): setup deployment`). Started on `main`; created
  `006-media-delivery-titles` from that commit.
- `.specify/feature.json` already contained
  `"feature_directory": "specs/006-media-delivery-titles"`; left unchanged.
- Preserved pre-existing tracked modification
  `.specify/scripts/python/__pycache__/common.cpython-314.pyc` and untracked
  `specs/006-media-delivery-titles/` design documents. No commits made.
- Prerequisite command:
  `python3 .specify/scripts/python/check_prerequisites.py --json --require-tasks --include-tasks`
  exited 0, reporting the expected absolute feature directory and research,
  data model, contracts, quickstart, and tasks documents.
- Specification checklist: 16 checked, 0 unchecked (PASS). No
  `.specify/extensions.yml` exists, so no implementation hooks are registered.
  Existing Python/Docker ignore files cover the relevant generated artifacts.

Environment observed before dependency changes:

| Component | Observed value |
|---|---|
| OS / architecture | macOS 27.0.1 (26A434), Darwin arm64 |
| uv | 0.13.1 (Homebrew 2026-10-14 aarch64-apple-darwin) |
| Locked project Python | CPython 3.13.16 |
| pytest / pluggy | 9.1.1 / 1.6.0 |
| pytest plugins | asyncio 1.4.0, anyio 4.15.1 |
| FFmpeg / ffprobe | 9.0.2 |
| Deno | 2.9.7 (aarch64-apple-darwin) |

Baseline command: `uv run --locked pytest` (exit 0).

```text
collected 787 items / 3 deselected / 784 selected
784 passed, 3 deselected, 20 warnings in 5.79s
```

The 20 warnings are existing python-telegram-bot `retry_after` deprecation
warnings: 18 from delivery error tests and 2 from runtime tests. The live tests
were deselected by the existing controlled-suite configuration. Baseline completed
before any dependency changes; evidence recorded at `2026-10-18T19:03:34Z`.

Pre-change SHA-256 values:

```text
57e962ad11f94078f31a6f61e8ec7ac712395e072258636061ed9140e7742a75  pyproject.toml
95602e7989bd36d0a2bdb62bd41b0695cc6c7878113c34827258729a8ac251a1  uv.lock
```

## T002 — Locked grapheme dependency (2026-10-18)

- Added exact runtime pin `regex==2026.8.31` to `pyproject.toml` and ran
  `uv lock` (exit 0): resolved 30 packages; only regex was added. A parsed
  comparison against `HEAD:uv.lock` confirmed every existing package record was
  unchanged except OpenMedia's new dependency metadata; all existing versions
  were retained. No upgrade flag was used.
- `uv sync --locked --group dev` exited 0, installed regex 2026.8.31, and rebuilt
  the editable OpenMedia installation. It reported the existing build-backend
  range warning: `uv-build>=0.12,<0.13` does not contain running uv 0.13.1.
  Installation succeeded; the backend range was left unchanged.
- `uv run --locked python` smoke assertions passed on CPython 3.13.16:
  regex imported as version 2026.8.31; `regex.findall(r"\X", value)` returned a
  single whole cluster for each of `e\u0301`, `🇫🇮`, `👍🏽`, and `👩‍💻`.
- Installed distribution metadata reports `Requires-Python: >=3.10`,
  `License-Expression: Apache-2.0 AND CNRI-Python`, and
  `License-File: LICENSE.txt`. Inspected installed
  `regex-2026.8.31.dist-info/licenses/LICENSE.txt` (11,584 bytes;
  SHA-256 `bff55ef4cdcc8c14ce259f8e8ab60e264418440d6335f4dc138273fbd506144d`).
  It contains the Apache-2.0 text and credits CPython 2.6/3.1 `re` derivation,
  Secret Labs AB (1998–2001), and CNRI's Python 1.6 license; additions and
  alterations are Apache-2.0 with Matthew Barnett (2020) attribution.
  No separate NOTICE file or full CNRI license text is listed in the installed
  regex distribution. This records the supplied wheel contents, without claiming
  a separate CNRI text was inspected.
- Added regex and its attribution/retention note to `THIRD_PARTY_NOTICES.md`.
  Added that notice summary to project `license-files`, alongside `LICENSE`, so
  the build backend includes it in distributions. Re-ran
  `uv sync --locked --group dev` successfully after this metadata change;
  installed OpenMedia metadata lists both `LICENSE` and `THIRD_PARTY_NOTICES.md`
  as `License-File` entries. The regex distribution remains
  installed unchanged with its own license file. Artifact/container inspection
  and notice-retention verification remain the T019 release gate.
- No application behavior or source files changed. No live source, Telegram,
  push, or deployment operations were performed.
- `git diff --check` passed.

## Remaining validation

Implementation acceptance, packaging/container checks,
configured startup, and requirements traceability remain to be recorded by their
corresponding tasks. Real Telegram caption, saved filename, and client behavior
remain unverified unless separately and explicitly authorized.

Phase 1 coordinator check: `uv run --locked pytest` passed: 784 passed, 3 deselected, 20 existing warnings (5.39s). `git diff --check` passed.
