# Source Adapter and Choice Contract

Extends [001 source adapters](../../001-media-download/contracts/source-adapters.md) and
[003 choice policy](../../003-streamlined-bot-ux/contracts/choice-policy.md).

## Inspection

Keep SourceRouter's YouTube → yt_dlp dispatch. YtDlpAdapter recognizes the trusted input
route, extracts the canonical single-item music URL with the current YTDLP_OPTIONS, and
checks platform and media identity. Feed optional trusted source-route context into
`normalize_info`; callers without it retain existing behavior.

Reject collections, entries, live/upcoming/post-live, malformed extraction output, and wrong
identity before applying AUDIO metadata. For music, override only metadata.canonical_url
and media_kind from the recognized route; source title, duration, and artwork keep existing
normalization. Ignore source title/category as an intent signal.

Emit only native audio candidates using current safe protocol, URL, extension, codec and
size rules. Do not construct merge pairs for music. No formats or video-only output becomes
`no_native_audio`; preserve source unavailability and invalid-response categories. Audio
candidates excluded by output size remain available for policy diagnosis.

## Selection

`choose(options, *, media_kind, max_file_bytes)` keeps its signature and accepts AUDIO.
Use existing audio ranking and return one automatic ID-0 choice or the audio-only missing
map described in data-model.md. Missing video choices must never appear on a music card.
Map empty audio `too_large` to TOO_LARGE, and audio `not_offered` to NO_NATIVE_AUDIO.
Other media kinds and their failure classification remain unchanged.

## Download, refresh, and delivery

Reuse native YtDlpAdapter.download, guarded resource reads, signature/stream verification,
size enforcement, and existing owned scratch directories. Audio-only download never calls
FFmpeg merge or a metadata-writing postprocessor. Source access remains anonymous.

An expired signed URL may use the existing single metadata refresh only for the established
refreshable category. Re-inspect the retained music canonical URL. The refreshed item must
match identity and exact selected native format by current `_same_option` rules; do not
silently upgrade, downgrade, or choose video. Existing deadlines include refresh work.

Test the worker metadata/error envelope round trip for AUDIO and new errors. Audio files
remain `send_document` deliveries with original native extensions and bytes. No new host
allowlist exemption, cookie jar, upload service, or worker protocol version is needed.

## Required controlled evidence

Music/plain and music/context normalization; ordinary YouTube regression; source returning
www.youtube.com webpage URL without losing intent; mixed video/audio input; no audio;
all audio oversized; unknown sizes; deterministic ties; malformed/collection/live results;
wrong identity; expired URL refresh retaining music canonical URL and selected audio;
native byte equality; worker serialization; no conversion or merge invocation.
