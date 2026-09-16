# Research: Media Download Workflow

**Date**: 2026-09-15
**Scope**: Resolve implementation choices for `spec.md`; document source evidence separately
from design decisions and future validation. Research does not establish live compatibility.

## 1. Python Telegram service

**Decision**: Python 3.13, python-telegram-bot 22.8, and long polling in a single Linux
container. Use asyncio for orchestration and short Telegram handlers; run blocking source
inspection and downloading in cancellable child processes. Keep request state in memory.

**Rationale**: This matches the constitution and the restart behavior already permitted by
the spec. It needs no inbound port, webhook deployment, separate web backend, database, or
queue service. python-telegram-bot provides asynchronous Telegram operations; its documented
22.8 release is the planning baseline. Bound update processing and size the HTTP connection
pool explicitly rather than accepting unconstrained concurrency.

**Alternatives considered**: aiogram is also suitable, but introduces no requirement-specific
advantage here. Webhooks add ingress configuration without a scaling requirement. A database
and task broker add durability that this feature explicitly does not require. Threads alone
cannot provide the required hard termination of stuck downloader work.

**Evidence**: [python-telegram-bot documentation](https://docs.python-telegram-bot.org/en/stable/),
[concurrency and connection pools](https://docs.python-telegram-bot.org/en/stable/telegram.ext.applicationbuilder.html),
[Python subprocess lifecycle](https://docs.python.org/3/library/asyncio-subprocess.html).

## 2. Telegram delivery and selection

**Decision**: Use Telegram's hosted Bot API and upload local files with `sendDocument` for
all output types. Set an application delivery ceiling of 50,000,000 bytes. Use inline
buttons with opaque request/option identifiers and answer every callback promptly.

**Rationale**: File attachments satisfy FR-009 and preserve original image/video/audio bytes
without Telegram photo processing or media-player format restrictions. The current hosted
API documents 50 MB document uploads and 1–64-byte callback data. Metadata and thumbnails
remain a separate preview; they are not the delivered media file.

**Alternatives considered**: Native video/audio presentation is optional future polish.
A local Bot API server supports larger uploads but adds a service; current scope already
permits explaining delivery limits. External hosting, splitting, and conversion are excluded
by the spec. Do not silently retry an upload after an ambiguous network failure: Telegram
may have accepted it, and another send can produce duplicates.

**Evidence**: [Telegram document delivery](https://core.telegram.org/bots/api#senddocument),
[inline button payloads](https://core.telegram.org/bots/api#inlinekeyboardbutton),
[local server capabilities](https://core.telegram.org/bots/api#using-a-local-bot-api-server).
The 50,000,000-byte ceiling is our conservative interpretation/configuration, not a promise
that all files at that boundary will be accepted. Recheck the documented limit before release.

## 3. Capacity, timeout, and recovery defaults

**Decision**: One service replica, two active work slots total, one active request per user,
and at most 100 pending previews. Inspection occupies a slot; awaiting selection releases it;
a selected download occupies a slot through delivery. When no slot is available, report busy
without queueing work. A busy selection remains pending until its original expiry.

Inspection has a 60-second total deadline, selection expires after 900 seconds, and download
plus delivery has a single 600-second deadline, as required by the spec. Use monotonic clocks.
Bound each work directory to 128 MiB and the runtime temporary filesystem to 512 MiB. Allow
2 CPUs and 2 GiB RAM initially, including the temporary filesystem. Capacity is a deployment
starting point to benchmark, not demonstrated throughput.

**Rationale**: These defaults bound publicly accessible work while keeping resource management
inside one service. They turn the spec's capacity placeholders into testable deployment
values. A successful selection must atomically claim both the request and a work slot.

**Alternatives considered**: Waiting queues change the specified busy behavior. Multiple bot
replicas need shared request ownership and coordination not required by the initial scope.
Automatic restart/resume conflicts with the permitted ephemeral request lifecycle.

Reserve the last five seconds of each inspection/processing deadline for cancellation
and reaping. On timeout or shutdown, terminate the entire worker process group, escalate
to kill within that reserve, reap children, close upload handles, and then delete temporary files. Sweep
leftovers at startup and every 60 seconds. Clear pending updates at process startup so old
link messages do not restart previously interrupted downloads. Old callbacks ask for a fresh
link. Record completion only after a successful Telegram response; delivery uncertainty must
never be presented as confirmed success or confirmed non-delivery.

## 4. Reproducibility and validation

**Decision**: Use `pyproject.toml` and a committed `uv.lock`, with `uv sync --locked` in
validation and image builds. Use pytest and pytest-asyncio for controlled workflow tests.
Pin the Python image, uv build tool, source dependencies, and any auxiliary runtimes in the
implementation artifacts; generate the lock from verified compatible releases rather than
inventing dependency hashes in this plan.

**Rationale**: Exact resolved dependencies make downloader changes reviewable. Reuse captured,
sanitized source responses for deterministic tests; separate credential-free live source
checks and opt-in Telegram delivery checks. Exercise workflow outcomes and external contracts
rather than writing tests that repeat configuration values.

**Alternatives considered**: Unpinned installation during startup hides upstream changes.
Always-live tests mix regressions with source outages. A broad CI/deployment platform rollout
is unnecessary for this feature.

**Evidence**: [uv Docker integration](https://docs.astral.sh/uv/guides/integration/docker/),
[Docker temporary filesystem limits](https://docs.docker.com/engine/storage/tmpfs/).

## 5. Public-input and diagnostic boundaries

**Decision**: Accept only recognized social post URL routes over HTTPS. Treat extracted URLs,
redirects, titles, filenames, and worker output as untrusted data. Validate every resolved
network destination before connection, including redirects and media requests; deny loopback,
private, link-local, multicast, reserved, and metadata-service addresses. Enforce this in all
worker transports, not only at initial URL submission. Pin connections to validated resolved
addresses while preserving TLS hostname verification so DNS changes cannot bypass the rule.

Use request-generated directory names and safe fixed basenames. Never invoke a shell with
user input or let downloaders load user configuration, cookies, plugins, proxy environment,
or executable postprocessing options. Give workers a minimal environment without the bot
token. Keep metadata previews escaped and length-bounded.

**Rationale**: Public URLs must not grant access to the host network or filesystem. Runtime
resource bounds are independent of public user access and do not introduce registration.

Emit structured stdout events with random request ID, platform, stage, duration, bytes, active
slot count, and error category. Exclude bot tokens, signed URLs, full source URLs, captions,
usernames, and raw upstream response bodies. Keep user/chat identifiers only in ephemeral
request state. Container log rotation is deployment configuration; no analytics or metrics
service is needed. Rate-limit status updates per chat and honor Telegram's retry-after response
only within the request deadline; never automatically retry an upload with an unknown outcome.

**Evidence**: [Telegram operational guidance](https://core.telegram.org/bots/faq).
These network and logging boundaries are project design decisions, not claims of controls
already supplied by the downloader libraries.

## 6. Source adapters and native-format policy

**Decision**: Use yt-dlp for video/native audio, Instaloader for Instagram image metadata,
and a narrow LinkedIn image adapter using the standard-library HTML parser. Implement the
LinkedIn adapter against the public embed route documented by ShareXtract, not generic
Open Graph images. Reuse relevant parsing ideas or attributed Apache-2.0 code where useful.

| Source | Inspection and download strategy | Required acceptance evidence |
|---|---|---|
| YouTube video | yt-dlp metadata-only inspection; select an exact source format ID | Public video with playable native format; native audio where exposed |
| LinkedIn video | yt-dlp LinkedIn post extractor | Public single video; identity and format preservation |
| LinkedIn image | Parse public activity embed for exactly one explicit image attachment; bounded HTTP file fetch after selection | Single image, multiple images, unrelated preview, missing descriptive fields, mismatched identity |
| Instagram video | yt-dlp; reject multi-item results | Public single video/reel; native audio only if independently available |
| Instagram image | Instaloader `Post.from_shortcode`; `GraphImage` picture URL; reject `GraphSidecar` | Public single image and carousel rejection |

**Rationale**: yt-dlp's LinkedIn extractor reads video elements; it does not implement image
attachments. Instaloader exposes explicit image/post-type metadata. The LinkedIn precedent
identifies image attachments in public embed HTML separately from article previews. Match
the requested activity ID, require exactly one attachment, and treat avatars/preview images
as metadata, never as the requested file.

**Alternatives considered**: yt-dlp alone misses images. gallery-dl supports Instagram but
has no documented LinkedIn route. Importing the whole alpha ShareXtract framework adds a
broader extraction surface; its LinkedIn extractor also rejects posts with neither author
nor text, conflicting with FR-004 when an image is still available. A narrowly scoped parser
retains the demonstrated attachment handling while allowing optional metadata to be absent.
This is a justified custom integration under Constitution IV, not a new extraction framework.

**Native-format boundary**: Select one independently downloadable source output. Never use
yt-dlp's default combined best-video-plus-audio selection, extraction/conversion postprocessors,
or automatic format fallback. Include existing combined audiovisual files when available;
otherwise label video-only outputs as silent. Audio-only formats must already be exposed by
the source. Omit choices requiring external remuxing or merging. This implements the user's
source-format choice without adding a separate merging feature or an FFmpeg dependency.
The eligible download-protocol allowlist is fixed in `contracts/source-adapters.md`.

**Integration controls**: Use metadata-only extraction before selection. Post/media-type
classification must precede format presentation; do not flatten carousels or playlists into
a single entry. On selection, refresh expired URLs only within the existing deadline and
only if the same media identity, format ID, quality, and audio inclusion remain available.
Do not save full media during inspection or confuse an image attachment download with an
optional thumbnail fetch. If no separate small thumbnail exists, omit it.

Use one Instagram work slot across both adapters, with parent-owned cooldown/rate state
surviving individual child exits. Instaloader's process-local rate accounting cannot be
assumed to coordinate fresh workers; its rate controller must consult the parent through
worker events. On 429, stop the operation and apply the reported cooldown (60 seconds if
absent). No login, cookies, browser impersonation, PO-token service, or paid proxy fallback
is part of this public-content feature. When source access is unavailable, explain that
outcome. Verify anonymous access from the intended deployment environment before release.

**Evidence**:
- [yt-dlp LinkedIn extractor](https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/linkedin.py)
- [Instaloader post structures](https://instaloader.github.io/module/structures.html)
- [Instaloader rate-limit assumptions](https://instaloader.github.io/troubleshooting.html)
- [LinkedIn public embed implementation](https://github.com/wuaishare/sharextract/blob/main/sharextract/extractors/linkedin.py)
- [ShareXtract package metadata](https://github.com/wuaishare/sharextract/blob/main/pyproject.toml)
- [gallery-dl supported sites](https://github.com/mikf/gallery-dl/blob/master/docs/supportedsites.md)

## 7. Dependency versions and license records

| Component | Planning constraint | Purpose and license handling |
|---|---|---|
| Python | `>=3.13,<3.14`; exact patch/base-image digest fixed in Dockerfile | Backend; retain Python distribution notices |
| python-telegram-bot | `==22.8` | Telegram integration; LGPL-3.0 library, retain notices and corresponding library source availability |
| yt-dlp | `yt-dlp[default]==2026.8.19` | Video/audio extraction; Unlicense core, retain dependency notices |
| yt-dlp-ejs | Compatible exact version resolved by yt-dlp extra and `uv.lock` | Bundled YouTube challenge scripts; retain upstream notices |
| Deno | `>=2.3.0,<3`; exact patch and checksum fixed in image build | yt-dlp JavaScript runtime; MIT and bundled component notices |
| Instaloader | `==4.15.3` | Instagram image metadata; MIT, with requests dependency locked |
| LinkedIn parser precedent | ShareXtract 0.23.4 source; record exact source commit if code is reused | Apache-2.0 attribution for any adapted code; no ShareXtract runtime dependency |
| pytest / pytest-asyncio | `pytest>=8,<10`, `pytest-asyncio>=1,<2`; exact compatible versions in lock | Development validation; retain distributed dependency notices |
| uv | `>=0.12,<0.13`; exact build-tool version/digest pinned | Dependency/build tooling; upstream MIT/Apache-2.0 notices |

The dependency license inventory belongs in `THIRD_PARTY_NOTICES.md` during implementation.
No project distribution license is chosen by this plan. Preserve the individual dependency
licenses and attribution; exact dependency closure and notices must be checked with the lock.

YouTube support needs both the EJS package and a supported JavaScript runtime. Bundle EJS
at build time, disable runtime remote component fetching, and give Deno no extra filesystem
or network permissions. Deno is an auxiliary tool, not another backend service.

**Evidence**: [yt-dlp release](https://github.com/yt-dlp/yt-dlp/releases/tag/2026.08.19),
[yt-dlp dependencies](https://github.com/yt-dlp/yt-dlp#dependencies),
[EJS runtime setup](https://github.com/yt-dlp/yt-dlp/wiki/EJS),
[Instaloader release](https://github.com/instaloader/instaloader/releases/tag/v4.15.3),
[Instaloader package](https://github.com/instaloader/instaloader/blob/master/setup.py),
[python-telegram-bot license](https://docs.python-telegram-bot.org/en/stable/#license).

## Research disposition

All design choices are resolved. No user clarification or scope change is required. Source
review establishes plausible integration paths, not working downloads: no live source media
or Telegram messages were fetched or sent in this planning phase. Preserve the complete
FR-002 platform/media matrix as a release gate. If credential-free representative examples
cannot pass during implementation, report the evidence and request a scope decision rather
than treating an inaccessible category as implemented. Dependency lock resolution, network
guard compatibility, and actual capacity/timing results are implementation validation gates.
