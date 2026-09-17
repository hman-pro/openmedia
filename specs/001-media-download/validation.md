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
