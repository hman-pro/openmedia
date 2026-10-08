# Research: YouTube Music Downloads

**Date**: 2026-10-08
**Scope**: Design research, repository inspection, and pinned upstream source review.
No live source extraction or Telegram delivery performed during planning.

## R1 — Reuse the pinned YouTube extractor

**Decision**: Keep `yt-dlp[default]==2026.8.19` and `player_client=default,android`.
Use its existing Youtube extractor for music watch links, through the current guarded
metadata client. Keep `noplaylist=True`, no credentials, no persistent cache, no plugins,
and no remote executable downloads.

**Rationale**: The pinned extractor includes music watch URL matching and music examples.
Its code distinguishes authenticated music client selection; this project stays anonymous.
Matching proves compatibility of the URL shape, not live download availability. No client
list change is justified without fresh live evidence as required by CLAUDE.md.
[Versioned extractor source](https://raw.githubusercontent.com/yt-dlp/yt-dlp/2026.08.19/yt_dlp/extractor/youtube/_video.py).

**Alternatives considered**: A new music-specific extractor duplicates upstream logic;
subscription/cookie access violates scope; invoking a separate downloader bypasses the
existing guarded network and worker limits. None is needed.

## R2 — Preserve music identity across refresh

**Decision**: Route music links as `platform=youtube`, `route_kind=audio`, canonical
`https://music.youtube.com/watch?v=<id>`. Set normalized `media_kind=audio` from trusted
input-route context, not source category or extractor title. Keep the music canonical URL
in metadata even when yt-dlp reports a regular YouTube webpage URL.

**Rationale**: `SourceRouter.download` refreshes expired transport URLs by inspecting
`metadata.canonical_url`. Canonicalizing to www.youtube.com would erase intent. Existing
worker serialization reconstructs `MediaMetadata` from its fields and supports a new enum
value without a separate request protocol. Ordinary music-themed YouTube videos remain videos.

**Alternatives considered**: A new platform breaks shared rate limits and identity checks;
a request-only flag does not survive refresh unless threaded through every boundary;
inferring intent from titles misclassifies ordinary videos. A canonical music route plus
one audio enum value fits the existing pipeline.

## R3 — Bound the shared-link grammar

**Decision**: Recognize only `/watch` with one nonempty `v` value matching the existing
YouTube ID grammar `[A-Za-z0-9_-]{6,64}`. Refuse all repeated `v` parameters, including
identical repeats and empty-value combinations (parse with blank values retained). Drop all
other query context from the canonical URL. Add exact `music.youtube.com` recognition to
host and bare-link normalization; reuse HTTPS upgrading and existing fragment refusal.
Music-specific handling occurs before ordinary YouTube's playlist rejection.

**Rationale**: This accepts a track shared from a playlist while guaranteeing one target.
The current project grammar remains stable; pinned extractor actual IDs are 11 characters,
so syntactically accepted but unextractable IDs still receive ordinary unavailable guidance.
Ordinary YouTube `list` rejection remains unchanged. Collection-only music URLs receive
single-track guidance; artist/search/home links receive unsupported-link guidance.

**Alternatives considered**: Passing list context upstream risks collection expansion;
allowing arbitrary subdomains widens supported input unnecessarily; tightening all YouTube
IDs changes existing behavior outside scope. Shortener support needs separate evidence.

## R4 — Reuse audio ranking, suppress video work

**Decision**: For music, normalize only native audio options (`vcodec=none`, audio present),
retain excluded audio candidates for size explanations, and do not generate video or merge
pairs. Add `MediaKind.AUDIO` handling in `choose`, reuse `_pick_audio`, rebind the one selected
option to ID 0, and expose only the audio missing reason on empty results.

**Rationale**: Existing audio selection prefers a known-size pool over unknown sizes,
then ranks higher bitrate, exact size ahead of estimated on ties, and lower normalized ID.
This is the feature 003 policy and must remain unchanged. Native supported extensions remain
m4a, webm, opus, and mp4 when genuinely audio-only. No source conversion is performed.
Empty-audio classification must not be affected by ignored video size or codecs.

**Alternatives considered**: MP3 conversion and extracting audio from combined files violate
byte preservation. A new ranking policy would diverge from the spec's explicit reuse.
Filtering only after presenting choices leaves misleading missing-video text and unnecessary
merge option generation.

## R5 — Reuse automatic lifecycle with precise music messages

**Decision**: Keep the existing atomic `publish_and_claim` path, normal track card, download
verification, and `send_document` audio delivery. A successful music ChoiceSet has no missing
video entries and no keyboard. Add a music-specific automatic status so it does not claim
there is only one upstream version when several audio versions were ranked.

**Rationale**: Current automatic status says “only version available”; it is inaccurate for
this workflow. Missing-audio guidance must suggest another public track, never choosing video.
Use dedicated error categories `no_native_audio` and `music_collection` for stable diagnostics
and clear music-specific guidance; preserve existing generic categories for other requests.
Known oversized audio gives existing `too_large`; no eligible native audio gives
`no_native_audio`. Network and identity failures keep existing categories.

**Alternatives considered**: Reusing generic format-unavailable text conflates changed formats
with absent native audio; globally changing ordinary video messages introduces regressions.
A second music progress message conflicts with the compact card workflow.

## R6 — Dependency and deployment review

**Decision**: No new packages, version upgrades, runtime tools, or services. Reuse existing
notices and container pins.

**Rationale**: yt-dlp core is Unlicense and compatible with the project's MIT distribution;
its default extras and bundled components remain covered by the existing dependency closure
and notices. python-telegram-bot (LGPL-3.0) supplies existing document delivery; Instaloader
(MIT) is unchanged and unrelated to music. FFmpeg remains under the existing distribution's
license obligations; the music path does not invoke conversion or merging. This feature
introduces no license change. [yt-dlp pinned license](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/LICENSE).

**Alternatives considered**: A dependency upgrade is unnecessary for supported URL matching;
a separate service or database has no requirement-based justification.

## R7 — Controlled evidence and live release gate

**Decision**: Controlled fixtures prove parser, ranking, intent, state, bytes, and failures.
Extend the opt-in manifest with public music plain/context cases, and record actual anonymous
inspection/download results separately. Require manual Telegram file delivery and container
build/startup checks before release support claims.

**Rationale**: Upstream authentication, region restrictions, and expiring streams cannot be
proven by matching source code or fixtures. Current live suite primarily checks adapter
operations, so it must explicitly assert music metadata and selected audio behavior.

**Alternatives considered**: Running uncontrolled source requests in routine tests would
violate the repository's test isolation; declaring live success from upstream examples alone
would overstate evidence. All design unknowns are resolved; runtime availability is a
validation obligation rather than a pending user decision.
