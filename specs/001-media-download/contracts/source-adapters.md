# Source Adapter and Worker Contract

## Operations

The parent calls a supervised worker through bounded newline-delimited JSON on stdin/stdout.
Worker stderr is captured and sanitized, never forwarded verbatim to users or routine logs.
The one permitted destination is the flagged diagnostic file of feature 002, which receives the
sanitized capture as `worker_output` on a failure entry (amended by 002).
Maximum serialized inspection result is 2 MiB; oversized/malformed results fail inspection.
Operations are fixed enum values, not arbitrary commands. No Telegram token or user/chat ID
is sent to the worker. Spawn using an argument array and a minimal environment.

| Operation | Input | Successful result |
|---|---|---|
| inspect | Validated source URL, request ID, parent-created directory, absolute monotonic deadline, response/output limits | MediaMetadata, normalized FormatOption list, and an optional thumbnail file of at most 1 MiB in that directory; no primary media |
| download | Source identity, exact selected option, parent-created directory, remaining deadline and byte limit | One regular file in that directory; actual bytes, format, media identity |

Events: `progress` (stage and bytes, at most once per second), `rate_request` (platform and
request class), `rate_limited` (platform and retry-after), `result`, or `error`. Parent answers
rate requests with a permitted delay or rejection using shared Instagram rate state; any
delay is inside the current deadline and never creates a queued user job. Rate counters are
updated before each upstream request, across successive workers. Only one terminal event is
valid. Process exit without a terminal result is a failed operation.

Error categories: `unsupported_url`, `unsupported_collection`, `unavailable`, `no_formats`,
`format_unavailable`, `too_large`, `rate_limited`, `timeout`, `storage_exhausted`,
`unsafe_destination`, `invalid_source_response`, `internal`. Include only sanitized metadata;
parent maps the category to the Telegram contract.

(amended by 004) Two more categories, `short_link_unresolved` and `short_link_not_post`, cover
LinkedIn short links. The terminal `error` event may carry an optional `"detail"` naming the
resolution outcome (`not_found`, `no_redirect`, `too_many_redirects`, `timed_out`,
`unreachable`, `outside_linkedin`, `not_a_post`). The parent ignores any other value. See
[linkedin-links.md](../../004-linkedin-share-links/contracts/linkedin-links.md#worker-protocol-change).

## Source routing and evidence

- YouTube: recognized video/watch/short-link/shorts routes, with collection/live URLs rejected.
  Inspect through yt-dlp without download. Preserve stable video identity and exact format ID.
- LinkedIn video: yt-dlp's explicit LinkedIn post extractor. Disable generic fallback to
  arbitrary web pages. Recognize the public post/activity routes supported by that extractor.
  (amended by 004) `posts/<slug>` addresses are recognized by type and numeric ID whatever
  their trailing code, and hyphen-code addresses reach yt-dlp through `OpenMediaLinkedInPostIE`.
  See [linkedin-links.md](../../004-linkedin-share-links/contracts/linkedin-links.md#recognized-inputs).
- LinkedIn short link (added by 004): `lnkd.in/p/<code>` is resolved in the inspect worker
  with one no-follow `HEAD` before any adapter runs, then routed as the post it names. See
  [linkedin-links.md](../../004-linkedin-share-links/contracts/linkedin-links.md#short-link-resolution).
- LinkedIn image: normalize the post activity ID to its public embed URL. Accept only one
  explicit feed-image attachment in the matching post, not an avatar, article cover, or
  Open Graph preview. Reject absent/ambiguous attachment identity and multiple attachments.
  Author/title remain optional. The parser is limited to this route and source shape.
- Instagram: normalize post/reel shortcode. Use yt-dlp video extraction and Instaloader image
  metadata; route based on media classification, not thumbnail presence. A single-image post
  yields its source image URL. Reject carousels and unproven single-item wrappers. Do not
  fetch primary image bytes merely to discover metadata or create a preview thumbnail.

Retain sanitized real upstream examples with provenance and expected media identity in
fixtures. Unit-made synthetic examples supplement but do not replace real source-shape
fixtures and release smoke checks. Never add login, account cookies, a cookie file, or
paid-service fallback when anonymous inspection fails. Cookies a source issues to a logged-out
visitor may be held in memory for one worker operation and discarded; they are never
persisted, shared across requests, or supplied by an operator. Only the Instagram metadata
client carries them, only between Instagram hosts, and a caller-supplied `Cookie` header is
always removed.

## Exact source-format downloads

Use explicit yt-dlp format IDs: one ID, or one `video+audio` ID pair for a merged choice.
Never use automatic best/merge selection or fallback. Disable postprocessors other than the
FFmpeg merger, thumbnail embedding, subtitle embedding, output conversion, external
downloaders, plugin loading, and persistent download archives. Eligible formats use yt-dlp
protocol `https` and are fetched as one resource (single or ranged requests). Treat `http`,
`m3u8`, `m3u8_native`, `http_dash_segments`, `f4m`, `ism`, `rtmp`, websocket, and any other
protocol as unavailable, even when fragments could be joined without FFmpeg: each fragment
downloader is a separate network path requiring its own guard binding. Adding a protocol
requires updating this allowlist, T039 transport tests, and live evidence.

YouTube inspection and download use `player_client=default,android` (research §6). The client
list is part of this contract and changes only with updated live evidence.

Combined video/audio files supplied by the source are eligible. Standalone video is silent;
standalone native audio is audio-only. A merged choice combines exactly one video and one
audio component by stream copy (`-c copy`, no re-encoding) into MP4 (`avc1` or `av01` with
`mp4a`) or WebM (`vp9` with `opus`). Both components must pass the protocol allowlist, and
their size sum governs cap eligibility. FFmpeg receives only local component files inside the
owned work directory, runs with `-nostdin` and `-protocol_whitelist file`, and is never used
as a downloader, so it adds no network path outside the guarded transports. For merged output,
validate the container signature and that it holds exactly the two selected streams with
their source codecs. Images retain the source-delivered file format, not
a claim about a creator's original pre-platform upload. Resolve format from trustworthy
metadata/headers and validate it against the downloaded signature. Reject inconsistent
metadata rather than renaming bytes into a different format.

A single metadata refresh may update expiring signed URLs within the remaining deadline,
but the media ID and selected format/quality/audio characteristics must remain identical.
Only an expired media URL (HTTP 403 or 410, classified from the status line before any body
is read) triggers the refresh; other upstream failures and failed media validation are
terminal, and the failed attempt's files are removed before the retry starts.
Re-inspection cannot pick the next-best format. Bound actual bytes regardless of reported
size and abort when the delivery cap is exceeded, including chunked responses. There is no
resume after a failed request; the user submits a fresh link.

## Network and file boundaries

Every worker network path (yt-dlp requests, Instaloader requests, direct-image and thumbnail
fetches, and redirects) must use the public-destination controls defined in research §5.
Implement transport-specific bindings to one tested policy; do not assume initial URL
validation covers later CDN requests. Disable alternate networking backends unless they
implement that same guard. Connections use validated IP endpoints with TLS hostname checks;
reject unsupported schemes, URL userinfo, and proxy environment inheritance. Redirects are
limited to five; strip sensitive upstream headers on host changes.
(amended by 004) `head` takes `follow_redirects: bool = True`. With `False` it returns the
first response, `3xx` included, with the raw `Location` header; only short-link resolution
uses it. See [linkedin-links.md](../../004-linkedin-share-links/contracts/linkedin-links.md#transport-change).

Metadata responses are capped at 8 MiB per response, thumbnails at 1 MiB and only from a
separate thumbnail URL. Output bytes are capped at 50,000,000, workspace usage at 128 MiB. A merge holds both
components and its output at once, so the workspace must be at least twice the output cap.
Parent validates a worker result path is a regular file inside its owned directory, with
no symlinks or traversal. File existence alone is not successful download evidence: check
size, native format, and source identity before sending. Downloader progress/file checks
and the container filesystem limit provide independent bounds.

Workers share no mutable extractor object or user session across requests. Kill/reap precedes
cleanup so timed-out processes cannot recreate removed files. Tests must verify that worker input/environment excludes the bot token, every network
transport rejects local/private destinations, and file results cannot escape the owned
request directory. These are application-boundary checks, not a claim that same-UID
subprocesses provide a hostile-code sandbox. Failing a guard is a defect to fix, not a
reason to disable the check.
