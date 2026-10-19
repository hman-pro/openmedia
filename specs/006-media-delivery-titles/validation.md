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

## Validation status

Controlled implementation acceptance, local packaging, and requirement reconciliation
are recorded below through T020. T019 remains open for container build/import, image
license inspection, configured startup, and running-container health. Real Telegram
caption, saved filename, forwarding, and client behavior remain unverified; no explicit
authorization for those checks has been supplied.

Phase 1 coordinator check: `uv run --locked pytest` passed: 784 passed, 3 deselected, 20 existing warnings (5.39s). `git diff --check` passed.

## Phase 2 / T003 — Foundation

Pure typed `derive_media_titles` API and frozen `DeliveryLabels` added, with values excluded from repr. Constants 64/240/fallback verified via Python 3.13 import, signature, immutability and repr assertions. Staged helper returns neutral labels pending T008. No logging/state or delivery changes. Coordinator reviewed source and `git diff --check` passed.

## Phase 3 — US1

T004 reviewed: helper test module quotes filename contract; `uv run --locked pytest tests/unit/test_media_titles.py -q` collected correctly, 4 expected assertion failures against staged fallback (source caption absent). Intended test-first checkpoint, not infrastructure failure.

T006 reviewed: music tests preserve embedded-tag fixture bytes, single document and automatic path; explicit literal labels added. Music module: 3 expected caption assertion failures, 5 passed (0.43s); current caption is absent and filename media.m4a.

T005 reviewed: 7 supported source/media final-upload cases and 3 preview policy checks added. Module run: 7 expected missing-caption assertion failures, 22 passed. Initial picture harness message-ID setup repaired before checkpoint; no remaining infrastructure errors. Method/hints/bytes/paths/state assertions precede intended failures.

T007 reviewed: four overlapping video/document cases (same and different titles) exercise real PTB multipart serialization. 6 passed, 4 expected label assertion failures; lifecycle, paths, bytes and overlap assertions passed.

T008 reviewed: ordinary source title and selected suffix derivation implemented with None fallback; unit tests 4 passed. Pure helper only; no file/content changes.

T009 reviewed: labels derive once after validated identity/file boundary, passed to both sends with explicit parse_mode=None and no caption entities. Existing retry/error/hint logic retained. Helper, delivery errors, download flow, music flow and isolation modules: 81 passed, 18 existing warnings.

## T010 — US1 controlled acceptance (2026-10-18)

Command (exit 0):

```text
uv run --locked pytest tests/unit/test_media_titles.py tests/integration/test_download_flow.py tests/integration/test_youtube_music_flow.py tests/integration/test_request_isolation.py tests/contract/test_delivery_errors.py
collected 81 items
81 passed, 18 warnings in 0.50s
```

Module totals: helper 4, download flow 29, YouTube Music flow 8,
request isolation 10, delivery errors 30. All 18 warnings are the existing
python-telegram-bot `retry_after` deprecation warnings.

Acceptance review confirmed:

- Seven general source/media cases cover YouTube video, silent video and audio,
  LinkedIn/Instagram video, and LinkedIn/Instagram pictures. Final uploads carry
  each fixture's source title and selected extension, explicit `parse_mode=None`,
  and no caption entities. Videos retain streaming and measured dimensions/duration;
  audio and pictures remain documents. File paths and exact uploaded bytes are unchanged.
- Titled music cases deliver one automatic document with the source track title
  and native `.m4a` filename. Byte equality includes the synthetic embedded title
  tag; no audio-player send, conversion, tag rewrite, or selection tap occurs.
- Four overlapping video/document cases retain request-local titles for different
  and identical source titles, separate owned paths, original bytes, and exactly
  one confirmed delivery per request. These also verify actual PTB multipart names.
- The three preview-policy cases retain the existing 200-character card policy
  and preview fallback. Existing automatic/manual paths, card counts, status
  sequence, and single media-send assertions pass without additional actions.
- Existing definite rejection, deadline-bounded RetryAfter, ambiguous-network
  no-resend, and changed-format/size rejection checks pass. Source review confirms
  labels derive only after file/identity validation and once before the retry loop;
  they remain upload metadata and do not rename or modify the local file.

Full controlled phase gate (exit 0):

```text
uv run --locked pytest
collected 805 items / 3 deselected / 802 selected
802 passed, 3 deselected, 20 warnings in 5.56s
```

The full suite's 20 warnings are the existing 18 delivery-error and 2 runtime
`retry_after` deprecation warnings. Live tests remained deselected.
`git diff --check` passed. No US1 defect was exposed and no runtime source fix
was necessary for T010. US2 normalization, filename safety, Unicode/byte limits,
and final release gates remain separate unfinished tasks; these results establish
the short safe-title MVP only. No live source, Telegram, push, or deployment
operation was performed.

## Phase 4 — US2

T011 reviewed: normalization/fallback/unsafe runs/reserved names/independent stem tests added, quoting data model. Unit run: 48 expected assertion failures, 14 passed, no infrastructure errors. Boundary shortening remains T015.

T012 reviewed: both send methods, imperfect metadata and frozen retries plus inherited errors/byte counts. Contract run: 42 passed, 12 expected normalization/sanitization assertion failures; infrastructure subset 38 passed.

T013 reviewed: original/missing title across expired/direct source URLs, production worker JSON boundary and real delivery. Refresh module 21 passed. These assertions pass existing intended retention behavior; no forced red checkpoint. No title-only inspection or schema fields added.

T014 reviewed: whitespace-before-control cleanup, Unicode preservation, display-empty fallback and independent safe stems implemented. Helper + delivery errors + download/music/isolation/refresh: 184 passed, 30 PTB deprecation warnings. No shortening until T015.

T015 worker checkpoint before source edits: 14 expected shortening assertion failures, 66 passed. Implemented regex iterator whole-grapheme prefix shortening with independent caption/stem budgets, extension/ellipsis byte reservations and final prefix trim. Coordinator reviewed source/tests and reran `uv run --locked pytest tests/unit/test_media_titles.py -q`: 80 passed in 0.03s. `git diff --check` passed. Cases cover all requested ASCII/Unicode/239–241-byte/oversized cluster/independent stem boundaries. Worker closed after coordinator verification; broader regression gate follows as T016.

## T016 — US2 controlled acceptance (2026-10-19 local)

Executed at `2026-10-18T22:45:17Z` (Europe/Helsinki local date 2026-10-19).
Targeted command (exit 0):

```text
uv run --locked pytest tests/unit/test_media_titles.py tests/contract/test_delivery_errors.py tests/integration/test_refresh.py tests/integration/test_download_flow.py tests/integration/test_youtube_music_flow.py tests/integration/test_request_isolation.py
collected 202 items
202 passed, 30 warnings in 1.64s
```

Module totals: helper 80, delivery errors 54, refresh 21, download flow 29,
YouTube Music flow 8, request isolation 10. All 30 warnings are the existing
python-telegram-bot `retry_after` deprecation warning exercised by retry cases.

Acceptance review confirmed:

- Missing, blank, whitespace/control/surrogate-only and invisible-only helper
  inputs use `Untitled media`. Both final send methods cover absent metadata,
  missing/display-empty titles, normalized whitespace, unsafe names, reserved
  basenames and literal Unicode/markup, with unchanged local names and bytes.
- Caption and filename stem limits are independent. The 63/64/65-point cases,
  CJK, decomposed accents, flags, modifiers and joined emoji retain whole
  graphemes without NFC/NFKC rewriting. Filename cases cover 239/240/241 complete
  UTF-8 bytes, 64 four-byte characters, extension/ellipsis reservations,
  oversize first clusters, and final stem trimming. Sanitization uses the full
  normalized source title before shortening.
- Four injected-clock retry cases cover video/document and original/missing
  title. Replacing request metadata during RetryAfter leaves both attempts'
  labels fixed, including the fallback; exact upload bytes and send counts pass.
- Four refresh/direct cases retain original title or fallback even when refresh
  supplies a different title. Real worker JSON serialization/decoding preserves
  the existing result field set, identity, exact selected format, owned path and
  bytes. Only an expired URL triggers the single inspection; valid URLs trigger
  no inspection and no title-only source request occurs.
- All US1 supported-source/media, music, preview-policy and overlapping-request
  regressions pass. Inherited definite rejection, deadline, ambiguous-send
  no-resend, invalid-output, changed-format/size and cleanup checks pass.

Full controlled phase gate (exit 0):

```text
uv run --locked pytest
collected 909 items / 3 deselected / 906 selected
906 passed, 3 deselected, 32 warnings in 5.78s
```

The full gate's warnings comprise 30 delivery-error and 2 runtime instances of
the same existing PTB deprecation warning. Live tests remained deselected.
`git diff --exit-code HEAD -- src/openmedia/models.py src/openmedia/workers.py src/openmedia/sources/__init__.py`
and the corresponding staged-diff check both exited 0: all three files remain
unchanged, with no schema expansion. `git diff --check` passed.
No title/delivery defect was exposed, so T016 required no runtime source fix.
No live source, Telegram, commit, push or deployment operation was performed.
Packaging/container, configured startup and real-client acceptance remain
separate release checks.

## T017 — Diagnostic regression and source audit (2026-10-19 local)

- Added two controlled automatic journeys to `test_diagnostic_trace.py` using
  the real `deliver_media` boundary and fake video/document sends. Each confirms
  the title sentinel reaches the actual caption and sanitized upload filename,
  the other send method is unused, and the existing seven diagnostic stages
  remain intact. A fixed inherited payload-key allowlist rejects added fields;
  the title sentinel is absent from every serialized diagnostic entry. Both
  stdout and stderr remain empty with a root console handler installed.
- Reviewed all of `src/openmedia/media_titles.py` and
  `src/openmedia/delivery.py`: labels are a frozen request-local pair, with both
  values excluded from repr. The pure helper introduces no request registry,
  cache, persistence, filesystem access, network/source requests, logging, or
  title-bearing exception text. Its module-level values are policy constants
  and compiled patterns only.
- Delivery reads the existing request metadata after file and identity validation,
  derives labels once before retries, and passes them only as Telegram upload
  metadata. Existing local file reads and sends remain; no local rename/write,
  source inspection, new storage/state, credential handling, or diagnostic fields
  were introduced. Existing failure results contain fixed categories and next
  steps rather than title values or raw credential-bearing exception text.
- `uv run --locked pytest tests/integration/test_diagnostic_trace.py -q`
  exited 0: **47 passed in 0.24s**. This includes both new title cases and all
  existing diagnostic journeys. No live source or Telegram request was made.

T018 coordinator and fresh verification review passed: four docs aligned with implemented labels and preview policy, 12 local link targets/README anchor/test paths checked, `git diff --check` clean. Original T017/T018 workers were closed after stalled reporting; fresh T017 replacement implemented privacy regression and fresh T018 verifier checked preserved docs. Stale planned-only wording in 006 contract is queued for T020 reconciliation.

## T019 — Final controlled and packaging checks (2026-10-19 local)

Evidence completed at `2026-10-19T02:33:34Z`. **T019 remains open**: local
controlled/package checks passed, but Docker build/import, configured container
startup and running-container health have not passed. No implementation defect
was exposed and no runtime/test file was changed for this task.

Executed commands and results:

```text
uv sync --locked --group dev
# exit 0; Resolved 30 packages in 3ms; Checked 26 packages in 0.63ms

uv run --locked pytest tests/unit/test_media_titles.py tests/contract/test_delivery_errors.py tests/integration/test_refresh.py tests/integration/test_download_flow.py tests/integration/test_youtube_music_flow.py tests/integration/test_request_isolation.py tests/integration/test_diagnostic_trace.py
# exit 0; collected 249; 249 passed, 30 warnings in 1.92s

uv run --locked pytest
# exit 0; collected 911 / 3 deselected / 908 selected
# 908 passed, 3 deselected, 32 warnings in 5.96s

uv build
# exit 0; built dist/openmedia-0.1.0.tar.gz
# and dist/openmedia-0.1.0-py3-none-any.whl
```

Focused module totals are helper 80, delivery errors 54, refresh 21, download
flow 29, music 8, isolation 10, and diagnostics 47. Warnings remain the existing
PTB `retry_after` deprecation (30 delivery-error cases; plus 2 runtime cases in
the full suite). The three live tests remained deselected. Build emitted the
existing backend-range warning that `uv-build>=0.12,<0.13` does not contain
running uv 0.13.1; both artifacts were successfully built.

Artifact and installed-distribution inspection ran through
`uv run --locked python - <<'PY'` using `zipfile.ZipFile`, `tarfile.open`,
`importlib.metadata.distribution`, and SHA-256 assertions (exit 0):

- Wheel `openmedia/media_titles.py` equals the source helper byte-for-byte.
  `openmedia-0.1.0.dist-info/licenses/THIRD_PARTY_NOTICES.md` equals the project
  notice byte-for-byte. Wheel METADATA contains
  `Requires-Dist: regex==2026.8.31` and
  `License-File: THIRD_PARTY_NOTICES.md`.
- Source distribution `openmedia-0.1.0/src/openmedia/media_titles.py` and
  `openmedia-0.1.0/THIRD_PARTY_NOTICES.md` equal their project files byte-for-byte;
  bundled `pyproject.toml` retains `regex==2026.8.31` and the notice license-files
  entry. Dependencies are installed separately rather than bundled into the
  OpenMedia wheel/sdist.
- Installed regex is 2026.8.31, with
  `License-Expression: Apache-2.0 AND CNRI-Python`,
  `License-File: LICENSE.txt`. Its sole listed license/notice file is
  `regex-2026.8.31.dist-info/licenses/LICENSE.txt`, 11,584 bytes, SHA-256
  `bff55ef4cdcc8c14ce259f8e8ab60e264418440d6335f4dc138273fbd506144d`.
  Assertions confirmed Apache License, Secret Labs, and Matthew Barnett text;
  this matches the supplied upstream license examined in T002. Image retention
  of that installed license remains unverified.

| Built artifact (absolute directory `/Users/homan/source/openmedia/dist/`) | Bytes | SHA-256 |
|---|---:|---|
| `openmedia-0.1.0-py3-none-any.whl` | 96,691 | `f45420a670fe4e68cfcb03877435a4a032349df3d9aa4e154663872990cb7ba7` |
| `openmedia-0.1.0.tar.gz` | 85,286 | `cea2a69a1c6f367cc965b84c78838b67e8d3f78bb7b2b4234b1b018427bae018` |

Docker and runtime availability:

```text
docker build --tag openmedia:local .
# exit 1:
ERROR: failed to connect to the docker API at unix:///Users/homan/.docker/run/docker.sock; check if the path is correct and if the daemon is running: dial unix /Users/homan/.docker/run/docker.sock: connect: no such file or directory

uv run --locked --env-file .env python -m openmedia --check-config
# exit 2:
error: No environment file found at: .env
```

The Docker client exists, but the daemon socket is unavailable. Container import
(`docker run --rm --entrypoint python openmedia:local -c 'import regex; import openmedia.media_titles'`),
image version/license inspection, and constrained read-only container
`--check-config` were not run because no successful image build/daemon is
available. No `.env` was supplied, so configured local/container checks remain
unavailable; no keyring or credential lookup was attempted.

A distinctly **synthetic local configuration smoke check** passed (exit 0),
using the exact following command. Captured application output was withheld;
the temporary work directory was automatically removed. This checks local
runtime prerequisites only and proves neither configured credentials nor
container readiness:

```sh
uv run --locked python - <<'PY'
import os, subprocess, sys, tempfile
from pathlib import Path
from datetime import datetime, timezone
with tempfile.TemporaryDirectory(prefix='openmedia-t019-config-') as temporary:
    env = os.environ.copy()
    env['TELEGRAM_BOT_TOKEN'] = '123456789:' + 'A' * 35
    env['OPENMEDIA_WORK_DIR'] = str(Path(temporary) / 'work')
    env['OPENMEDIA_DIAGNOSTIC_LOG'] = '0'
    result = subprocess.run([sys.executable, '-m', 'openmedia', '--check-config'], env=env, capture_output=True, text=True)
    assert result.returncode == 0, 'synthetic config check failed'
    assert 'configuration valid' in result.stdout
    print('Synthetic local --check-config: exit 0; configuration valid; captured output withheld; temporary work directory removed on exit')
print('Evidence UTC:', datetime.now(timezone.utc).isoformat())
PY
```

Configured polling startup and health of a running container remain unverified.
Polling contacts Telegram and was not authorized; it was not attempted. The
README's read-only root, 2 CPU/2 GiB limits, bounded 512 MiB tmpfs, UID/GID and
health procedure were reviewed, but none is claimed as executed container
evidence. No real Telegram message, polling, live-source request, deployment,
push, or credential-bearing output occurred.


## T020 — Requirements reconciliation and external acceptance (2026-10-19 local)

**Disposition:** implemented; controlled acceptance verified; external release gates pending. Actual branch is `006-media-delivery-titles` (confirmed with
`git branch --show-current`). This reconciliation reviews the implemented helper,
delivery boundary, and acceptance assertions against every FR and SC. It uses the
final post-review repair results: **285 focused passed** and **944 full controlled passed**,
with **3 live tests deselected**. Named tests below were included in those successful
runs; parameterized names denote all their cases. The original T020 documentation reconciliation used T019 results; the coordinator
updated this matrix after the fresh repair workers reran the checks below. Test paths are repository-relative.

| Requirement | Concrete controlled evidence and implementation review | Disposition |
|---|---|---|
| FR-001 | `tests/integration/test_download_flow.py::test_source_title_is_on_the_final_media_call_without_changing_delivery` passes seven source/media cases, including YouTube, LinkedIn and Instagram. `tests/integration/test_youtube_music_flow.py::test_plain_track_automatically_delivers_one_unchanged_document` passes titled music contexts. Both assert the actual final caption, explicit `parse_mode=None` and no caption entities. `delivery._send` supplies the common caption to both send methods. | Verified in controlled acceptance; real-client display unverified. |
| FR-002 | The same seven general cases and titled music contexts assert final filenames, selected extensions and existing video/document methods. `tests/unit/test_media_titles.py::test_identical_title_uses_each_selected_extension` and `test_source_suffix_is_preserved_before_selected_extension` pass. `derive_media_titles` appends only the validated selected extension; `_send` passes its filename as upload metadata. | Verified in controlled acceptance; client saved filenames unverified. |
| FR-003 | `tests/unit/test_media_titles.py::test_display_empty_title_uses_neutral_fallback` covers missing, blank, control-only and invisible-only titles. `tests/contract/test_delivery_errors.py::test_imperfect_titles_are_upload_labels_only` confirms absent metadata and display-empty titles succeed with `Untitled media` on both send methods, one upload and unchanged bytes. `_normalize_title` provides the fallback without further inspection or user action. | Verified in controlled acceptance, including default-ignorable-only regressions; see resolved audit below. |
| FR-004 | `tests/unit/test_media_titles.py::test_title_normalization_produces_one_readable_line`, `test_literal_markup_and_unicode_are_preserved_in_caption`, `test_ascii_code_point_boundary_and_extension_exclusion`, `test_shortening_keeps_longest_whole_grapheme_prefix` and `test_first_cluster_larger_than_code_point_budget_yields_only_ellipsis` pass. `_normalize_title` normalizes whitespace before removing controls and preserves joiners/selectors; `_shorten` iterates regex `\X` and reserves the terminal ellipsis within 64 code points without Unicode normalization. Literal upload parsing is also asserted by the delivery contract cases. | Verified in controlled acceptance; client rendering unverified. |
| FR-005 | `tests/unit/test_media_titles.py::test_filename_sanitization_preserves_literal_caption`, `test_reserved_device_basename_is_prefixed`, `test_unusable_filename_stem_falls_back_independently`, `test_sanitization_runs_before_independent_caption_and_stem_shortening`, `test_shortened_filename_prefix_trims_final_spaces_and_dots`, `test_complete_filename_byte_boundary_reserves_suffix_and_ellipsis`, `test_sixty_four_four_byte_characters_need_only_filename_shortening` and `test_first_cluster_larger_than_byte_budget_yields_only_ellipsis_stem` pass. `_safe_stem` replaces unsafe runs and trims outer dots/spaces; independent `_shorten` budgets reserve the dot, extension and ellipsis, enforcing whole graphemes and 240 complete UTF-8 bytes. No label is used as a local path. | Verified in controlled acceptance, including invisible-only stems; client save compatibility unverified. |
| FR-006 | `tests/integration/test_request_isolation.py::test_concurrent_delivery_titles_and_owned_files_remain_request_local` passes four cases (same/different titles, video/document) with separate paths and actual PTB multipart filenames. `tests/integration/test_refresh.py::test_delivery_keeps_original_title_and_worker_schema_across_source_refresh` passes four original/missing-title and valid/expired-URL cases. `tests/contract/test_delivery_errors.py::test_retry_after_freezes_original_labels_even_if_metadata_changes` passes four cases. Coordinator retains request metadata; router refresh replaces only the option; `deliver_media` freezes labels before its retry loop. Missing titles retain fallback: adopting newly available metadata is MAY, not required. | Verified in controlled acceptance; no mix-ups. |
| FR-007 | General source/media cases assert selected formats, measured video hints, unchanged local paths and exact uploaded bytes. `tests/integration/test_youtube_music_flow.py::test_plain_track_automatically_delivers_one_unchanged_document` compares bytes including an embedded source title tag, forbids merge/conversion/tag rewriting, and forbids audio-player mode. `_send` opens the original downloaded file as before and only adds upload labels. | Verified in controlled acceptance; real-client playback/byte retrieval unverified. |
| FR-008 | General source/media and music cases assert existing status sequences, card counts, automatic/manual behavior and one final media call. `tests/integration/test_download_flow.py::test_delivery_title_policy_does_not_replace_the_preview_card_title_policy` preserves the separate 200-character preview policy. Existing `tests/contract/test_metadata_clients.py::test_no_cookie_file_is_configured_for_ytdlp`, `test_other_platforms_never_record_or_send_cookies` and `test_operations_share_no_cookies`, plus `tests/integration/test_request_isolation.py::test_preview_expiry_terminal_ttl_limit_and_restart_invalidation` and `tests/integration/test_failure_cleanup.py::test_music_workflow_deadline_cancels_stalled_callbacks`, pass in the full suite. Failure/retry checks below retain limits and duplicate prevention. Source review finds no extra message, source call, state, deadline or cleanup change in the helper/delivery integration. | Verified in controlled acceptance; external operational gates remain pending. |
| FR-009 | `tests/integration/test_diagnostic_trace.py::test_delivery_titles_stay_out_of_diagnostics_and_console` passes video/document journeys: title reaches upload labels, diagnostic payload keys stay within the inherited allowlist, title sentinel is absent from logs, stdout/stderr are empty. `test_identifiers_appear_once_and_never_on_the_console` passes inherited privacy checks. T017 source audit confirms frozen request-local labels with values excluded from repr, no new persistent storage/logging/network access and no title-bearing or credential-bearing exception text. | Verified by controlled regression and source audit. |
| SC-001 | The seven `test_source_title_is_on_the_final_media_call_without_changing_delivery` cases and three titled contexts in `test_plain_track_automatically_delivers_one_unchanged_document` pass correct final captions/filenames for all supported sources and delivery types. Concurrency cases additionally verify actual serialized multipart labels for the correct request. | All titled controlled acceptance cases pass; manual Telegram confirmation pending. |
| SC-002 | The helper module's 116 passing cases and 16 `test_imperfect_titles_are_upload_labels_only` cases cover fallback, literal Unicode/markup, unsafe names, independent budgets and intact extensions. `test_ascii_code_point_boundary_and_extension_exclusion` explicitly covers 63/64/65; `test_shortening_keeps_longest_whole_grapheme_prefix` covers CJK, decomposed accents, flags, modifiers and ZWJ emoji; `test_complete_filename_byte_boundary_reserves_suffix_and_ellipsis` explicitly starts at 239/240/241 UTF-8 bytes and asserts every final complete filename fits 240 bytes. | All controlled boundary and imperfect-title cases pass, including default ignorables and complete tag flags; see resolved audit below. |
| SC-003 | General source/media, music and imperfect-title upload tests compare exact selected/uploaded bytes and retain original paths. General acceptance asserts the existing selection only where needed; music forbids selection and automatically sends one unchanged document. Label derivation performs no file write, content/tag modification or user interaction. | All controlled acceptance deliveries preserve bytes and add zero user actions. |
| SC-004 | Four `test_concurrent_delivery_titles_and_owned_files_remain_request_local` cases, four `test_delivery_keeps_original_title_and_worker_schema_across_source_refresh` cases and four `test_retry_after_freezes_original_labels_even_if_metadata_changes` cases pass. `tests/contract/test_delivery_errors.py::test_ambiguous_network_outcome_is_unknown_and_never_retried` and `tests/integration/test_request_isolation.py::test_duplicate_selection_and_replacement_never_publish_stale_work` pass. Definite RetryAfter rejections permit the next attempt; ambiguous outcomes do not resend. | Zero title mix-ups or duplicate confirmed deliveries in the controlled set. |
| SC-005 | Full-suite `tests/contract/test_bot_errors.py::test_invalid_or_multiple_supported_links_are_rejected`, `test_unavailable_names_possible_causes_without_asserting_one` and `test_every_adapter_error_has_sanitized_guidance` pass inherited unsupported/inaccessible guidance. Focused `tests/integration/test_download_flow.py::test_every_video_candidate_over_the_limit_fails_as_too_large` and `test_picture_over_the_delivery_limit_fails_as_too_large`, plus `tests/contract/test_delivery_errors.py::test_definite_rejections_are_failed`, `test_retry_after_past_deadline_is_not_retried`, `test_ambiguous_network_outcome_is_unknown_and_never_retried`, `test_changed_format_or_size_is_rejected_before_send` and `test_title_labels_do_not_change_pre_upload_failures`, pass expected categories/send counts. Full-suite failure/cleanup regressions also pass. Validation remains before title derivation and inherited failure handling is unchanged. | Existing controlled failure acceptance outcomes retained. |

### Resolved implementation findings from final audit

Both independently reproduced findings are repaired and pass regression checks:

- FR-003/005: `test_default_ignorable_only_title_uses_neutral_fallback`,
  `test_default_ignorables_with_visible_text_are_preserved`, and
  `test_filename_separators_and_default_ignorables_use_fallback_stem` cover
  U+034F, U+115F/U+1160, U+17B4/U+17B5, U+3164/U+FFA0 and mixed sequences.
  Unicode Default_Ignorable_Code_Point determines fallback visibility without
  deleting retained characters inside otherwise visible titles.
- FR-004/005 and SC-002: `test_complete_emoji_tag_flags_are_preserved`,
  `test_tags_outside_complete_flag_sequences_are_removed`, and
  `test_tag_flag_shortening_preserves_whole_sequence_at_both_budgets` preserve
  valid subdivision flag sequences, remove stray/incomplete tags, and keep
  complete flag graphemes within independent caption/filename budgets.
  Research section 4 now documents the narrow Cf exception required to preserve
  visible Unicode. No functional requirement was weakened.

### External acceptance and release gaps

No real Telegram messages, live-source requests, polling, deployment or push were
authorized or performed for T020. Optional manual acceptance from
[quickstart.md](quickstart.md#optional-real-telegram-check) remains **unverified**:

- Caption appearance on real video and YouTube Music messages, including a long or
  Unicode title where available; no client/version observation was collected.
- Actual saved filenames, filename preservation on forwarding, and client-specific
  save/rendering behavior. Fake transport and PTB multipart assertions establish
  upload labels only.
- Real-client playback behavior and downloaded/native-byte comparison. Controlled
  byte equality and unchanged embedded-tag assertions are not external evidence.

These limitations apply to the external interpretation of FR-001–002, FR-004–005,
FR-007 and SC-001–003; they do not change the specified requirements or invalidate
the recorded controlled results. No source platform's current live availability
is claimed by controlled fixtures.

T019 remains **open**: Docker build failed because its daemon socket was absent;
image import/version/license retention, configured container startup and running
health remain unverified. `.env` was absent, so configured local/container
`--check-config` remains unavailable. The successful synthetic local configuration
smoke check is neither configured startup nor container readiness. Polling requires
separate authorization because it contacts Telegram. Wheel/sdist builds and local
license inspection passed as recorded in T019, but do not close these release gates.

T020 changes only validation/specification/contract documentation, removes stale
specification-only status, and reconciles the inherited contract cross-references.
No functional requirement or success criterion was weakened. All implementation
hooks remain absent (`.specify/extensions.yml` does not exist, as recorded in T001).

## Independent final review and repairs

Read-only independent review confirmed two Unicode acceptance gaps: default-ignorable-only text bypassed fallback (FR-003/005), and valid emoji tag flags lost their tag characters during Cf cleanup (FR-004). Other delivery/state/byte/retry/privacy findings were clear; external release gates remained open. Fresh workers repair each defect sequentially.

First repair reviewed and integrated: compiled Unicode Default_Ignorable_Code_Point property now determines only fallback visibility, preserving retained characters alongside visible text. New standalone/mixed/separator regressions: RED 16 failed/88 passed; GREEN helper104, focused273 (30 warnings), full932 passed/3 deselected (32 warnings); uv build and artifact/notice checks passed. Final artifacts will be rebuilt after the second repair, so intermediate hashes are not release evidence.

Second repair reviewed and integrated: complete black-flag/tag-spec/cancel-tag
sequences survive normalization; unrelated Cf and stray/incomplete tags remain
removed. RED 6 failed/110 passed; GREEN helper116, focused285 passed (30 PTB
warnings, 1.89s), full944 passed/3 deselected (32 PTB warnings, 5.71s).
`uv build` passed; final wheel/sdist contain byte-identical current helper and
THIRD_PARTY_NOTICES.md, exact regex pin; installed license inspection passed.
Final rebuilt artifact SHA-256 values (supersede intermediate T019 hashes):

- `dist/openmedia-0.1.0-py3-none-any.whl`: `5a83b640231c28ea857f24d6568919ee54d99924089e1ef99536fd90902fc7b7`
- `dist/openmedia-0.1.0.tar.gz`: `c6ac8e17c00c7a52a166e4fa674df36d5aba5f8b0ecdf9f55bdaf1c3b7dd2eaa`

The existing uv/backend-range warning remains non-fatal. T019 container/configured
release checks remain open for the previously recorded environment limitations.

## Final coordinator handoff

A fresh independent reviewer approved the final implementation after both repairs,
with no remaining actionable findings. It independently reran focused acceptance:
285 passed; diff whitespace checks, all reconciliation test names, packaged helper
and final artifact hashes matched. All FR-001–009 and SC-001–005 have controlled
acceptance evidence in the matrix above. T020 is complete because unauthorized
manual checks are explicitly documented as unverified; T019 remains unchecked.

Phase 5 implementation/documentation work is finished and committed at its boundary;
release readiness is blocked by the recorded external gates. All workers are closed.
No push, deployment, real Telegram message or live-source check was performed.
The unrelated pre-existing tracked bytecode modification remains untouched.
There is no `.specify/extensions.yml`; pre/post implementation hooks are absent.

Resume T019 with a functioning Docker daemon and supplied runtime configuration:
follow quickstart build/import/license/configuration checks. Startup/polling and
manual real Telegram checks require appropriate authorization and must remain
unverified until actually executed. Do not treat local builds or synthetic config
as container readiness. Final controlled suite: 944 passed, 3 deselected, 32 PTB
retry_after deprecation warnings; package build and notices verified. The known
uv 0.13.1/backend range warning is non-fatal and recorded above.
