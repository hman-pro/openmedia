# Validation record

Implementation validation evidence for feature `001-media-download`. Each section records
what was actually run, not what is expected to work.

---

## T059 — Source feasibility spike

**Date**: 2026-09-16
**Network location**: Local developer workstation (macOS, Apple Silicon), ordinary
consumer/office egress. **Not** the deployment network. Per `quickstart.md` the live source
matrix must be re-run from the intended deployment network before release; a pass here does
not predict a pass from a datacentre IP range, which several sources treat differently.
**Tool versions**: yt-dlp 2026.08.19, yt-dlp-ejs 0.8.0, Instaloader 4.15.3, Deno 2.9.6,
CPython 3.13.15.
**Method**: Metadata-only inspection. No primary media was downloaded and nothing was
committed. Instagram requests were spaced more than 60s apart.
**Sanitization**: Signed CDN URLs, their `t=`/`e=` tokens, and LinkedIn `rcm=` share-tracking
parameters are deliberately omitted below. They identify the sharer or expire, and neither
belongs in version control.

### Summary

| Category | Anonymous access | Combined video+audio | Verdict |
|---|---|---|---|
| YouTube video | Pass | **Yes**: source-muxed format 18, or stream-copy merge | Pass — decision recorded below |
| LinkedIn video | Pass | Yes | Pass |
| LinkedIn image | Pass | n/a | Pass |
| Instagram video | Pass | Yes | Pass |
| Instagram image | Pass (carousels) | n/a | **Provisional pass — approved; closes in T017** |

Four of five categories pass. Instagram image holds a provisional pass approved by the
project owner on 2026-09-16: anonymous access and CDN image fetches were shown on two
carousel posts, but no single-image (`GraphImage`) post was inspected. Per T059, that
approved decision allows Phase 2 to start. The gap closes in T017, which must capture its
`GraphImage` fixture from a live single-image post, and the T054 live suite repeats it.

### YouTube video — a native combined format exists, but only via a non-default client

Examples: `jNQXAC9IVRw` (19s, 2005) and `aqz-KE-bpKQ` (635s, 4K). Inspected with
`yt-dlp -J --no-playlist`, exit 0, no warnings, no cookies, no PO token.

**Default client result.** With yt-dlp's default client selection (it negotiated `visionos`
here), both examples return **zero** formats carrying both a video and an audio codec, and
the historically muxed format `18` is absent. Verified explicitly, not inferred:
`format 18 present: False`, and a direct scan for formats with both codecs returns zero,
including the HLS (`m3u8_native`) variants.

**Non-default client result.** Re-running with
`--extractor-args "youtube:player_client=android"` (and identically with `mweb`) returns
format `18`: a single progressive MP4, `avc1.42001E` + `mp4a.40.2`, 360p, plain HTTPS.
**This is one native file with sound. No merging, no remuxing, no FFmpeg.**

| Video | Duration | Muxed format | Size | Under 50,000,000-byte cap |
|---|---|---|---|---|
| `jNQXAC9IVRw` | 19s | 18 @ 240p | 0.6 MB | Yes |
| `aqz-KE-bpKQ` | 635s | 18 @ 360p | 28.5 MB | Yes |
| `dQw4w9WgXcQ` | 213s | 18 @ 360p | 11.8 MB | Yes |
| `kJQP7kiw5Fk` | 282s | 18 @ 360p | 23.4 MB | Yes |
| `9bZkp7q19f0` | 252s | 18 @ 360p | 15.7 MB | Yes |
| `JGwWNGJdvx8` | 263s | 18 @ 360p | 11.1 MB | Yes |

Format 18 was present on **6 of 6** videos that extracted successfully. Three further IDs
failed extraction outright (`BaW_jenozKc` reports "This video is unavailable"); those are
absent videos, not videos lacking a muxed format, and must not be counted either way.

### Does yt-dlp's own merging avoid the FFmpeg dependency? No.

Tested directly, because "yt-dlp can merge" is true but incomplete. With FFmpeg absent from
the machine, `yt-dlp -f "bestvideo+bestaudio"` reports:

```
WARNING: You have requested merging of multiple formats but ffmpeg is not installed.
         The formats won't be merged
```

and writes **two separate files** (`.f395.mp4` and `.f251.webm`). yt-dlp has no internal
muxer; `--merge-output-format` shells out to FFmpeg. Choosing merge therefore means bundling
FFmpeg in the image and delivering a container the service produced. An earlier draft of this
record called that a constitution exception; it is not. Principle III permits supporting
tools "needed by a chosen downloader or media processor". The native-only rule lived in the
feature spec, plan, and `CLAUDE.md`, which were amended instead. The downloaded test files were deleted; nothing was committed.

### Decision (2026-09-16)

Chosen by the project owner: **FFmpeg stream-copy merging, delivery cap unchanged at
50,000,000 bytes, `player_client=default,android`.** Written into research §6 and §7, both
source-adapter and runtime contracts, `data-model.md`, spec FR-006 and its assumptions,
`plan.md`, `CLAUDE.md`, and tasks T008, T016, T021, T035, T039, T048, T051, T057, plus new
task T060.

**Why the cap stays at 50,000,000 bytes.** 100 MB was requested, then set aside after checking
the live Bot API documentation on 2026-09-16: "Bots can currently send files of any type of
up to 50 MB in size, this limit may be changed in the future." Uploads up to 2000 MB need a
local Bot API server, which is a second service and a plan revision. That is deferred to a
possible separate feature.

**Why the client list is not `android,ios`.** Both were requested. `ios` returned no usable
formats: "Some ios client https formats have been skipped as they are missing a URL. YouTube
may have enabled the SABR-only streaming experiment". Fetch probe on `dQw4w9WgXcQ`, one 64 KiB
ranged request per format; signed URLs were never printed or stored:

| `player_client` | Formats listed (of 18, 136, 137, 398, 399, 248, 140, 251) | Ranged fetch |
|---|---|---|
| `default,android` | All eight | All HTTP 206 |
| `default` | All eight in this run; no format 18 in the first spike run | All HTTP 206 |
| `android` | 18 only; adaptive formats skipped (SABR) | 18: HTTP 206 |
| `tv_simply` | 18 only; warns a PO token is needed for the rest | 18: HTTP 206 |
| `web_embedded` | 18, 136, 140 among 41 formats | 136 and 140: **HTTP 403** |
| `mweb` | 18 only; warns a PO token is needed | 18: **HTTP 403** |

`web_embedded` is the lesson: it lists a full adaptive set that cannot be downloaded. Listing
is not evidence of availability.

**What fits under the cap.** Merge projections for `dQw4w9WgXcQ` (213 seconds), using exact
component sizes and the 3.4 MB m4a stream `140` as the audio component for every row. WebM
pairs would use an Opus stream in practice, so their totals are approximate.

| Height | `avc1` → MP4 | `av01` → MP4 | `vp9` → WebM |
|---|---|---|---|
| 480p | 17.6 MB | 13.3 MB | 12.8 MB |
| 720p | 29.9 MB | 21.0 MB | 21.1 MB |
| 1080p | **84.4 MB, over** | 33.9 MB | 34.3 MB |
| 1440p | — | **125.6 MB, over** | **154.6 MB, over** |

Size scales roughly with duration, so 1080p AV1 at this bitrate crosses 50,000,000 bytes at
about five minutes. Longer videos will offer 1080p only as silent video, and the preview must
say why.

**Merge verified end to end.** With FFmpeg 9.0.1 installed, yt-dlp merged explicit ID pairs
from `dQw4w9WgXcQ` using `player_client=default,android`, `--merge-output-format`, and
`--postprocessor-args "Merger+ffmpeg_i:-protocol_whitelist file"`:

| Pair | Output | Streams | Video packets | Audio packets |
|---|---|---|---|---|
| `160+140` | MP4, 5,571,480 bytes | h264, aac | Identical to source | Identical to source |
| `278+251` | WebM, 4,975,577 bytes | vp9, opus | Identical to source | Identical to source |

"Identical" is measured, not assumed: the SHA-256 `streamhash` of each output stream equals
that of the matching downloaded component, which shows stream copy with no re-encoding. The
protocol whitelist does not break yt-dlp's merger, and it refuses network input:
`Protocol 'https' not on whitelist 'file'!`. Components and outputs were deleted afterwards.

The development FFmpeg is Homebrew's build, configured with `--enable-gpl --enable-version3`,
so it is GPL-3.0-or-later. The image build pins its own FFmpeg, and T051 records that build's
licence, which may differ.

The client probe is one video in one session; T054 repeats the live checks from the
deployment network.

### LinkedIn video — pass

Example: public post `urn:li:ugcPost:7504928712690176000`. The public embed endpoint
`https://www.linkedin.com/embed/feed/update/urn:li:ugcPost:<id>` returned HTTP 200 (~25 KB)
anonymously. The `<video class="share-native-video__node">` element carries a
`data-sources` JSON array with two progressive MP4 renditions (720p and 640p, both
`video/mp4`, `crf28`), plus a poster image and a `data-digitalmediaAsset-urn` giving stable
item identity. Progressive MP4 means audio and video arrive in one file: **a combined option
exists and needs no merging.** Candidate transport is plain HTTPS to `dms.licdn.com`; the
source URLs are signed and expiring, so they must be treated as short-lived transport
references and never surfaced in callback data.

### LinkedIn image — pass

Example: public post `urn:li:share:7505650038253965312`. The public embed endpoint returned
HTTP 200 (~22 KB) anonymously, and the canonical post page returned HTTP 200 as well. The
embed holds exactly one `feedshare-image-high-res` attachment on `media.licdn.com` (asset
`D5622AQGXXQzo-AgFLQ`); the other three `<img>` elements are `static.licdn.com` interface
assets, and there is no `<video>`. A `HEAD` on the attachment returned HTTP 200,
`image/jpeg`, 319,737 bytes. The same asset appears in the canonical page and in `og:image`.
That match is coincidental for this post: `og:image` is an article preview on link posts, so
the parser must select the explicit attachment, never the Open Graph image.

An earlier example, `urn:li:share:7505167757483634688`, returned HTTP 404 from both the
canonical URL and the embed endpoint, serving the generic `<title>LinkedIn</title>` shell.
From outside, a deleted post and a gated one look the same. Keep it as a negative case: an
unavailable post must produce the "not publicly accessible" outcome, not a parser error.

### Instagram video — pass

Examples: shortcodes `DdMjtx2ttRz` and `DdEYWm3tlb7`, both `/reel/` URLs, inspected with
`Post.from_shortcode` anonymously and more than 60s apart. Both returned
`typename: GraphVideo`, `is_video: True`, `mediacount: 1`, and a populated video URL. The
`mediacount: 1` result matters: it confirms these are single items, so the carousel-flattening
failure mode that `data-model.md` warns about is not being masked. No rate limiting or login
prompt was encountered on either request.

### Instagram image — provisional pass, single-image path unverified

Example: shortcode `DdNByGRiAeh`, a `/p/` URL, inspected anonymously with
`Post.from_shortcode` well over 60s after the previous Instagram request. Access worked, but
the post is `typename: GraphSidecar` with `mediacount: 4`: a carousel, which FR-002 and
research §6 exclude.

This is useful negative evidence. `Post.url` on the carousel still returned a fetchable image
(`HEAD` 200, `image/jpeg`, 59,679 bytes, `scontent-*.cdninstagram.com`), which is the first
item. An adapter that read `url` without checking `typename` would silently deliver one image
from a four-image post, which is exactly the flattening failure `data-model.md` warns about.
Keep this shortcode as a candidate for the T017 `GraphSidecar` rejection fixture.

A second example, shortcode `DdVVcKbCJej`, was also a carousel: `GraphSidecar`,
`mediacount: 10`. Two findings came with it:

- **CDN format varies by post.** Its first-item `Post.url` served `image/webp` (38,534 bytes),
  where the previous carousel served `image/jpeg`, with the same request headers. The
  delivered format therefore cannot be assumed from the platform; detect it from response
  headers and file signature, as `contracts/source-adapters.md` already requires, and label
  the preview with what was actually served.
- **Instagram URLs may carry a username prefix.** It was supplied as
  `instagram.com/<username>/p/<shortcode>/`. yt-dlp's `InstagramIE` matches this form and the
  unprefixed form for both `/p/` and `/reel/` and extracts the same ID (offline regex check).
  The bot's own URL recognition must accept both forms, or users pasting links shared from the
  app will be told the link is unsupported.

**Decision (2026-09-16):** the project owner approved a provisional pass rather than supply
a third example. Rationale: anonymous access, the Instaloader shortcode path, and HTTPS CDN
image fetches are shown on two posts, and a single-image post differs in `typename` and
item count rather than in access path. Risk accepted: the `GraphImage` branch enters Phase 2
unexercised against a live response. Closure is assigned, not left open: T017 must capture a
`GraphImage` fixture from a live single-image post, and T054 repeats the check from the
deployment network.

Until then the category still lacks a single-image example (`GraphImage`, `mediacount: 1`). The anonymous
path and CDN format (`image/jpeg` over HTTPS) look the same as for the carousel, but that has
to be shown on a single-image post rather than assumed.

### T017 closure — Instagram single image

On 2026-09-16, Instaloader 4.15.3 anonymously inspected public shortcode `gbStjFIaB4` from
the local developer network. It returned `GraphImage`, `mediacount: 1`, `is_video: false`,
and a Helsinki Instagram CDN host. After more than 60 seconds, a 16-byte range probe of the
native image returned HTTP 206, `image/jpeg`, and JPEG/JFIF signature
`ffd8ffe000104a4649460001`. The signed URL and personal metadata were not recorded. Together
with T059's JPEG/WebP sidecar observations, the sanitized fixtures and six controlled
contract tests now exercise single-image normalization, missing optional metadata, both
recorded carousel rejections, media/thumbnail separation, and header/signature agreement.
This closes the provisional local GraphImage evidence; T054 still requires repetition from
the intended deployment network.

---

## T002 — Dependency resolution

`uv lock` resolved 29 packages against CPython 3.13.15, and `uv sync --locked --group dev`
exits 0. All planned pins resolved exactly as specified in `research.md` §7:
python-telegram-bot 22.8, yt-dlp 2026.8.19, Instaloader 4.15.3, pytest 9.1.1,
pytest-asyncio 1.4.0. The `yt-dlp[default]` extra pulled in yt-dlp-ejs 0.8.0 as anticipated.
No compatibility failure occurred and no stack change was required.

---

## T031 — Controlled US1 integration

**Date**: 2026-09-16

`uv run --locked pytest tests/unit tests/contract tests/integration` passed **103 tests**.
The focused US1 set covers sanitized yt-dlp metadata for YouTube/LinkedIn/Instagram video,
the live-captured sanitized Instagram `GraphImage` shape, LinkedIn guest embed attachment
shapes, native option labeling/pagination, guarded adapter transports, exact selection and
originating-chat delivery, and actual FFmpeg MP4/WebM stream-copy behavior. The mocked
independent workflow test observes checking → downloading → sending, proves no primary media
download occurs before selection, verifies exact selected bytes/format/chat, and records
completion only after a confirmed Telegram message identity.

This is controlled fixture and subprocess evidence, not live matrix evidence. T026 remains
open because `OPENMEDIA_LIVE_MANIFEST` is not supplied; running the opt-in suite without it
produces one documented skip rather than a pass. No Telegram message was sent during this
controlled validation.

---

## T039–T040 — Controlled failure and boundary validation

**Date**: 2026-09-16

The focused transport, cleanup, worker, and merge gate passed **27 tests**. The adapter
contract suite now drives YouTube, Instagram-image, and LinkedIn-image download bindings
through `GuardedHTTPTransport` with a private-address DNS result and confirms that every path
rejects the destination before creating output. It also verifies the fixed 50,000,000-byte
output limit, 128 MiB workspace limit, request-owned output basename, and 1 MiB thumbnail
limit. Existing network and merge tests cover the 8 MiB metadata bound, traversal/symlink
rejection, peak merge workspace, local-only FFmpeg inputs, and `file` protocol whitelist.

Worker stderr is now sanitized before retention. A subprocess test emits a signed media URL
and Telegram-token-shaped value and proves neither survives in the captured diagnostic.
The complete controlled suite then passed **154 tests**. Injected unavailable content,
unsupported routes, missing formats, size/storage failures, worker protocol failures,
timeouts, blocked delivery, definite rate limits, ambiguous delivery, failed notifications,
and cleanup paths all ended with their required classifications while the US1 exact-byte
happy path remained green.

---

## T047 — Controlled request-isolation validation

**Date**: 2026-09-16

The same **154-test** controlled run includes the coordinator and callback acceptance suites.
They cover two independent users, duplicate and forged callbacks, replacement races, stale
worker publication, pending expiry, restart-invalidated/missing IDs, global and Instagram
capacity, 100-preview admission, terminal TTL/eviction, and preservation of a pending choice
when selection capacity is busy. No cross-user delivery or duplicate work was observed in
the controlled scenarios.

---

## T048–T052 — Runtime, notices, and complete controlled gate

**Date**: 2026-09-16

`uv sync --locked --group dev` resolved 29 packages and checked the 25 installed project/dev
packages without changing the lock. The required command
`uv run --locked pytest tests/unit tests/contract tests/integration` then passed **162 tests**
in 0.96 seconds. Three warnings are the documented python-telegram-bot 22.8 transition of
`RetryAfter.retry_after` toward `datetime.timedelta`; no test failed or skipped.

The runtime contract suite covers local/redacted configuration, required Deno/FFmpeg tools,
fresh/stale heartbeat and successful-poll state, health checking without a second poller,
private atomic health-file replacement, and static image constraints. Existing subprocess
tests prove termination/reaping before cleanup and no surviving delayed child write.

`openmedia:local` built successfully for Linux arm64. The build installed only the 19 locked
runtime distributions, including yt-dlp-ejs 0.8.0. Container smoke checks under a read-only
root, 2 CPUs, 2 GiB memory, and 512 MiB noexec tmpfs passed configuration validation with a
redacted dummy token. The image runs as UID/GID 10001, exposes no ports, uses SIGTERM, and
contains Deno 2.9.6 plus Debian FFmpeg 5.1.9 (`7:5.1.9-0+deb12u1`). `ffmpeg -version` records
`--enable-gpl` and no `--enable-nonfree`; the resulting GPL-2.0-or-later obligation and the
full locked runtime closure are documented in `THIRD_PARTY_NOTICES.md`.

This is partial T053 evidence only. A real bot token was not available, so polling readiness,
health after a successful Telegram poll, manual delivery, and clean shutdown of a live bot
container were not claimed.

### Requirement review

| Requirement | Controlled evidence | Remaining release evidence |
|---|---|---|
| FR-001, FR-003–FR-008, FR-010–FR-016 | Pass: input, preview, exact selection, failures, isolation, deadlines, cleanup, public access contracts | Manual Telegram confirmation remains in T054 |
| FR-002, FR-006 | Pass for sanitized real-shape fixtures and exact native/stream-copy outputs | Five-category live matrix T026/T054 |
| FR-009 | Pass with fake Telegram confirming originating-chat `sendDocument` semantics and ambiguous-send handling | Real Telegram delivery T053/T054 |
| SC-001 | Controlled end-to-end paths pass | Live five-category end-to-end run T026/T054 |
| SC-002, SC-003 | Capacity and timing instrumentation are implemented | 20-inspection and 20-delivery timing runs T055 |
| SC-004 | Pass across every specified injected invalid, unavailable, limit, resource, and timeout class | None beyond final live smoke |
| SC-005 | Pass for controlled two-user/repeated/forged callback scenarios | Independent real accounts T054 |
| SC-006 | Pass: one submitted link and one first-page selection | Real Telegram happy path T054 |
| SC-007 | Pass for accelerated expiry, busy state, cleanup, restart invalidation, and real child termination | Live container shutdown portion of T053 |

Unresolved external gates remain explicitly open: T026 has a private five-source manifest but
needs fresh credential-free LinkedIn video and single-image examples; T053 needs a dedicated
Telegram bot token; T054 needs the intended deployment network and two test accounts; T055
needs the recorded 20+20 live timing run. No controlled substitute is counted as passing those
tasks.

---

## T026 — Live suite attempt remains incomplete

**Date**: 2026-09-16  
**Network**: local developer network, Helsinki  
**Versions**: Python 3.13.15, yt-dlp 2026.8.19, Instaloader 4.15.3, Deno 2.9.6,
FFmpeg 9.0.1 (local Homebrew build)

The private live manifest used the five credential-free examples already documented by this
report. The first run exposed an implementation defect: the yt-dlp allowlist named the stale
`LinkedInPost` extractor key instead of the installed extractor's `LinkedIn` key. A controlled
contract assertion was added, the fixture was corrected, and the focused 14-test yt-dlp/
transport gate passed.

After that fix, the live suite successfully completed its alphabetically first Instagram
image and Instagram video inspect/download/identity checks, including the required shared
60-second spacing, before reaching LinkedIn. It then failed because the recorded LinkedIn
video post `7504928712690176000` no longer exposed a video to the anonymous yt-dlp extractor,
and its public embed was unavailable to the image fallback. The previously recorded image
post `7505650038253965312` was likewise unavailable. Focused anonymous probes of three public
search-indexed posts (`7275224371206504449`, `7455440016459251712`, and
`7500526685084270592`) also returned unavailable through the required guarded adapters.

Because the suite stops on the LinkedIn failure, the YouTube case was not reached in this run.
No category error is counted as support, and no task is marked complete: T026 still needs fresh
credential-free LinkedIn video and single-image examples that pass on the target network, then
a complete five-category run with exact outputs recorded. T054 remains blocked on that evidence
as well as its separate Telegram checks.

---

## Final controlled verification

**Date**: 2026-09-16

The Python 3.13.15, uv 0.12.15, and Deno 2.9.6 image references were additionally pinned to
their resolved OCI digests. `docker build --tag openmedia:local .` then completed successfully,
and the rebuilt image passed `--check-config` with token redaction under a read-only root, 2 CPU,
2 GiB memory, and a 512 MiB noexec tmpfs. This does not substitute for the live-token portion of
T053.

After the LinkedIn extractor-key correction, the complete locked controlled gate was rerun:
`uv run --locked pytest tests/unit tests/contract tests/integration` passed **162 tests** in
1.03 seconds, with only the three already-documented python-telegram-bot deprecation warnings.
`git diff --check` also passed. The task ledger closes 56 of 60 tasks and deliberately leaves
T026, T053, T054, and T055 open for the external evidence described above.

---

## T091 — Convergence remediation and current controlled gate

**Date**: 2026-09-17

The sections above are accurate records of 2026-09-16 and are left unchanged. Three
convergence reviews followed. Each reviewed the code against `spec.md`, `plan.md`, the contracts,
and the constitution, and appended remediation tasks (Phases 7–9, T061–T093). This section
records the controlled evidence for those remediations and corrects the requirement review.

### Gate

`uv sync --locked --group dev` resolved 29 packages and checked 25 installed packages without
changing the lock. `uv run --locked pytest tests/unit tests/contract tests/integration` passed
**255 tests** in 2.78 seconds with no failures or skips; the one deselected test is the opt-in
`live` suite. The five warnings are the documented python-telegram-bot 22.8
`RetryAfter.retry_after` deprecation, now emitted by two tests. `git diff --check` passed.
The suite grew 162 → 224 (Phase 7) → 247 (Phase 8) → 255 (Phase 9).

Local tool versions for this run: Python 3.13.15, python-telegram-bot 22.8, yt-dlp 2026.08.19,
Instaloader 4.15.3, Deno 2.9.6, and **FFmpeg 9.0.1 (Homebrew)**. The container image bundles
FFmpeg 5.1.9; the merge tests therefore prove stream-copy behavior on the development host, not
inside the image. The image has not been rebuilt since Phase 7 changed worker environment,
shutdown, and FFmpeg ceilings; that rebuild belongs to T075.

### Remediations and their evidence

| Tasks | Remediation | Controlled evidence |
|---|---|---|
| T061 | Secrets and signed URLs never reach parent logs | `test_parent_logs_redact_transport_and_exception_secrets`, `test_worker_diagnostics_redact_signed_urls_and_bot_tokens` |
| T062, T082 | Failures notify once with stage and next step; notification never blocks finalization | `test_runtime_failure_is_notified_after_capacity_release`, `test_inspection_failure_and_notification_failure_release_everything`, `test_all_excluded_preview_sends_exactly_one_notice_saying_nothing_fits` |
| T063 | Workers find bundled tools with private scratch and no secrets | `test_worker_environment_keeps_trusted_tools_and_private_scratch`, `test_worker_environment_is_minimal` |
| T064, T092 | Absolute 60s/600s deadlines include status sends and uploads; workers stop at the request deadline less the 5s reap reserve | `test_total_inspection_deadline_includes_status_send`, `test_total_processing_deadline_marks_interrupted_upload_unknown`, `test_workers_receive_request_deadline_less_reap_reserve` |
| T065, T077, T084 | Claimed selections always start or finalize; repeats report processing; the chosen option is named | `test_claimed_job_starts_despite_callback_transport_failure`, `test_owner_chat_message_state_and_option_bounds_are_atomic`, `test_accepted_selection_names_the_chosen_option_after_scheduling_work`, `test_downloading_status_names_the_selected_option` |
| T066 | Shutdown cancels work, reaps child groups, cleans, and never overruns | `test_application_stop_cancels_tracked_work_before_waiting`, `test_shutdown_reaps_real_child_group_cleans_workspace_and_removes_health`, `test_application_stop_never_raises_past_its_budget` |
| T067, T073, T086 | Thumbnail previews keep every label; absent audio-only is explained; every excluded choice is explained or summarized | `test_long_thumbnail_preview_keeps_every_option_and_audio_guidance`, `test_every_excluded_choice_is_explained_or_summarized` |
| T068 | Delivery limit applied at inspection, including projected merges | `test_projected_oversize_and_unknown_merges_are_not_selectable`, `test_rejects_incompatible_pairs_and_excludes_exact_oversize`, `test_adapter_limits_and_fixed_output_paths_are_forwarded` |
| T069 | One refresh for expired URLs only, exact identity kept, attempt artifacts removed | `tests/integration/test_refresh.py` (13 tests) |
| T070 | yt-dlp and Instaloader requests are bounded and report upstream limits | `tests/contract/test_metadata_clients.py` (8 tests) |
| T071 | FFmpeg output and peak workspace ceilings enforced while running | `test_merge_enforces_peak_workspace_limit`, `test_merge_refuses_incompatible_or_network_input_and_caps_output` |
| T072, T089 | Descendants reaped after leader exit; cleanup retried inside the 900s ceiling; `--check-config` deletes nothing while polling startup sweeps | `test_exited_leader_with_pipe_holding_descendant_returns_and_is_reaped`, `test_transient_cleanup_retries_on_next_sweep`, `test_worst_case_sweep_alignment_stays_inside_cleanup_ceiling`, `test_check_config_keeps_workspaces_but_polling_startup_sweeps_them` |
| T078 | Ordinary sends honor 1/s per chat and 20/s overall without cross-chat blocking | `test_send_limiter_*` (4 tests) |
| T079 | Measured timing and external-failure attribution in logs | `test_timing_events_record_measured_preview_ack_and_upstream`, `test_request_logs_separate_service_timing_from_external_failures`, `test_telegram_failures_are_attributed_only_when_external` |
| T081 | Links from Telegram URL/text-link entities, scheme-less and `http://` forms | `test_links_are_taken_from_telegram_url_and_text_link_entities`, `test_handler_passes_extracted_links_to_the_workflow`, `test_scheme_less_link_in_plain_text_is_recognized_without_entities` |
| T083, T087, T088 | Distinct busy guidance; post-selection limit advice; group replies only for links | `test_busy_admission_outcomes_have_distinct_guidance`, `test_limit_failure_after_selection_advises_resubmitting`, `test_group_messages_get_guidance_only_when_they_contain_a_supported_link` |
| T085, T093 | LinkedIn author/caption from post markup only; attachment probe status classified before headers | `test_available_creator_and_caption_come_from_the_post_markup_only`, `test_unclosed_caption_paragraph_does_not_hide_the_attachment`, `test_attachment_probe_status_is_classified_before_headers` |
| T090 | Startup verifies bundled EJS | `test_runtime_requires_bundled_ejs_challenge_scripts` |

For T085, the public embed for activity `7505650038253965312` was re-fetched anonymously on
2026-09-17 to record the author and caption element shape (see
`tests/fixtures/linkedin/PROVENANCE.md`). The live page parsed to one attachment with both
fields present. This confirms the parser shape only; it is not T074 live-matrix evidence.

### Corrected requirement review

The 2026-09-16 review marked these rows as passing on controlled evidence. The convergence
reviews found real gaps in them, now fixed by the tasks shown, so those earlier passes were
incomplete:

| Requirement | Gap found after the earlier review | Fixed by |
|---|---|---|
| FR-001 | Scheme-less, `http://`, and hyperlinked links were rejected; group chatter got replies | T081, T088 |
| FR-004, FR-005 | Thumbnail previews could lose labels; LinkedIn images dropped available author/caption | T067, T085 |
| FR-006, FR-008 | Expired-URL refresh was incomplete and media validation checked only a prefix | T069 |
| FR-010 | Delivery limit not applied consistently at inspection; FFmpeg ceilings checked only afterwards | T068, T071 |
| FR-011 | Failure notification was not wired into the real handlers, then sent twice for all-excluded previews | T062, T082 |
| FR-012, FR-013 | Selection handoff could strand capacity; repeats looked stale; busy outcomes shared one message | T065, T077, T083 |
| FR-014, FR-015 | Deadlines excluded status sends and uploads; cleanup retries and descendant reaping were incomplete | T064, T072, T092 |
| US1/AC3 | The accepted choice was not identified to the user | T084 |
| US1/AC7 | Absent native audio-only was not explained in the preview | T073 |
| US2/AC2, US2/AC4, US2/AC5 | LinkedIn probe errors were misclassified; excluded choices could go unexplained; post-selection limit advice pointed to a closed preview | T093, T086, T087 |
| US3/AC1, US3/AC6 | The user's own active request and service capacity received the same busy message | T083 |

With these fixes, every FR-001–FR-016 row passes on controlled evidence. The live and release
columns of the earlier review are unchanged: controlled tests are not live evidence.

### Still open

T026 and T074 (five-category live source matrix), T053 and T075 (constrained container with a
real bot token, including a rebuilt image), T054 and T076 (deployment-network sources and
two-account Telegram acceptance), and T055 and T080 (20 + 20 live timing runs). No controlled
test is counted toward any of them.

**On hold (2026-09-21)**: T053 and T075 are paused by operator decision and stay open. T055 and
T080 wait with them, because timing taken outside the constrained container would not be
acceptance evidence. T026/T074 and the non-container parts of T054/T076 proceed; any result
gathered before the hold is lifted is recorded as run outside the container. FR-014, FR-015,
and the live-shutdown portion of SC-007 keep their T053 evidence gap, so feature 001 is not
reported complete while the hold stands.

---

## T026 follow-up — LinkedIn failure diagnosis

**Date**: 2026-09-17

**Network**: local developer machine

**Versions**: as in the T091 gate above (yt-dlp 2026.08.19)

The 2026-09-16 T026 attempt recorded every LinkedIn example as unavailable. These read-only
anonymous probes used the application's own `GuardedHTTPTransport` and `YtDlpAdapter` to find
out why. Only status codes, sizes, and parser outcomes were recorded; no post text.

**User-Agent is not the cause.** The default `OpenMedia/0.1` agent and a browser agent returned
byte-identical responses for all four embed requests tested.

**The URN type is the cause.** LinkedIn `activity`, `ugcPost`, and `share` URNs are distinct
objects even with the same digits, and a guest embed exists only under the post's own type:

| Post | `share` embed | `ugcPost` embed | `activity` embed | Content once reachable |
|---|---|---|---|---|
| `7505650038253965312` (recorded image) | 200 | not probed | not probed | One attachment; parses. The 09-16 failure was transient. |
| `7504928712690176000` (recorded video) | 404 | 200, public `<video data-sources>` | 404 | Video still public |
| `7455440016459251712` | 404 | 200 | 404 | Multiple images; correctly `unsupported_collection` |
| `7275224371206504449` | 404 | 404 | 200 | No media; yt-dlp `no_formats` |
| `7500526685084270592` | 404 | 404 | 200 | No media; yt-dlp `no_formats` |

`recognize_source_url` discards the URN type and canonicalizes every post to
`feed/update/urn:li:activity:<digits>`, and the image adapter always requests the `share` embed.
A post of any other type is therefore requested as an object that does not exist. The three
search-indexed posts were also never valid single-video or single-image examples.

The pinned yt-dlp `LinkedInIE` accepts only `/posts/<slug>-<id>-xxxx` and
`feed/update/urn:li:activity:<id>`; its own test case is a `ugcPost` in the `/posts/` form.
Handing it `feed/update/urn:li:activity:<ugcPost digits>` yields "Unable to extract video", and
`feed/update/urn:li:ugcPost:<id>` has no matching extractor. A `/posts/` URL with an invented
slug returns 404, so the video path cannot be confirmed without a real share link.

**Decision**: preserve the URN type and the user's `/posts/` link through routing (T094). The
video fix remains unconfirmed until T074 runs with real "Copy link to post" examples for one
video and one single-image LinkedIn post. No LinkedIn category is counted as passing.

**After T094**: through the real `SourceRouter`, adapters, and `guard_public_sockets`,
`feed/update/urn:li:share:7505650038253965312` inspected to one exact-size JPEG choice with a
creator, and its metadata link re-recognized to the same route; the `ugcPost` multi-image post
`7455440016459251712` was reached and rejected as `unsupported_collection` instead of a 404.
The locked controlled gate passed **269 tests**. This is image-path routing evidence only;
the video path and both LinkedIn T074 categories still need real share links.

---

## T074 partial — LinkedIn live probe and T095 (2026-09-21)

**Scope**: LinkedIn video and LinkedIn image only, run outside the container (T053/T075 are on
hold) from a development machine, anonymously, with yt-dlp 2026.8.19 and FFmpeg/ffprobe 9.0.2.
The probe repeated the `tests/live/test_sources.py` sequence per case: recognize, inspect
through the real `SourceRouter` and `GuardedHTTPTransport`, download the smallest selectable
choice, `validate_owned_file`, delete. T074 stays open: the required five-category run through
the live suite still needs YouTube and both Instagram examples.

**Sanitization**: both examples were supplied as `lnkd.in` share links and resolved from the
301 `Location` header only. The `utm_*` and `rcm=` share-tracking parameters are not recorded;
only the URN type and numeric identity are kept here.

| Case | Source identity | Before T095 | After T095 |
|---|---|---|---|
| LinkedIn video | `ugcPost` `7507745133358940161`, `/posts/` link with a percent-encoded non-Latin slug | Fail: `no_formats` from `normalize_info`, surfaced as `unavailable` after the image-adapter fallback | Pass: inspect 1.2 s, two selectable native MP4 choices of unknown size; format `1` downloaded unchanged, 13,989,818 bytes, MP4 signature and ffprobe check of exactly one video plus one audio stream passed |
| LinkedIn image | `share` `7507478518860132352`, `/posts/` link | Pass | Pass: inspect 1.4 s, one exact-size JPEG choice with creator, 153,775 bytes downloaded and matching the advertised size |

**Cause of the video failure**: the pinned `LinkedIn` extractor returned two progressive MP4
renditions with `vcodec`, `acodec`, dimensions, and sizes all `None`, distinguished only by
`tbr` (477 and 652 kbps). `normalize_info` coerced a `None` codec to `"none"`, so an unknown
stream was read as an absent one and both renditions were dropped. The controlled suite did not
catch it because `tests/fixtures/ytdlp/linkedin-video.json` carries explicit `avc1`/`mp4a`
codecs, a height, and an approximate size that the live extractor does not supply. The T094
routing fix is confirmed for the video path: the `ugcPost` `/posts/` link reached the extractor
and matched.

**T095**: `None` now means unknown-and-present and only `"none"` means absent, per codec. No
codec is stored in `transport_ref` for an unknown stream, so the post-download codec-family
comparison is skipped while the stream-count check still runs; a rendition that turned out to
lack audio would fail as `format_unavailable` rather than be delivered mislabeled. Evidence:
`test_unknown_codecs_are_present_not_absent`, `test_unknown_codecs_never_pair_for_merging`, and
the real-shape fixture `linkedin-video-progressive.json`. Locked controlled gate:
`uv run --locked pytest tests/unit tests/contract tests/integration` — **345 passed**.

**Findings recorded, not fixed**:

1. `lnkd.in` share links are rejected as `unsupported_url`; LinkedIn's share action now hands
   out this form. Supporting it means one guarded redirect lookup before recognition whose
   target must itself be a supported host. Scope decision, no task yet.
2. LinkedIn video choices have unknown size until download, so the 50,000,000-byte limit is
   enforced only after selection. A guarded HEAD probe, as the image adapter already does, would
   give exact sizes at preview time.
3. When yt-dlp fails on a `/posts/` link the router falls back to the image adapter, which
   replaces the original category (here `no_formats`) with `unavailable`.
4. The video inspection returned no creator; whether the extractor exposes one for this post
   was not examined.
