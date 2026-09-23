# LinkedIn Links Contract (004)

Extends `specs/001-media-download/contracts/source-adapters.md` for LinkedIn. It covers
which addresses are recognized, how a short link is resolved, and which adapter receives the
result. Field details are in [data-model.md](../data-model.md), and reasons in
[research.md](../research.md).

## Recognized inputs

| Input | Route | Notes |
|---|---|---|
| `https://lnkd.in/p/<code>` | `short_link` | Also `http://` and bare `lnkd.in/p/…`, upgraded to HTTPS like other hosts. Query dropped; a fragment is rejected as for every route |
| `https://lnkd.in/<anything else>` | none, `unsupported_url` | Out of scope |
| `https://www.linkedin.com/posts/<slug>` | `post` | Slug rule of research R6. Trailing code may contain hyphens. Raw non-Latin text allowed |
| `https://www.linkedin.com/feed/update/urn:li:<type>:<id>` | `post` (activity) / `embed` (ugcPost, share) | Unchanged |

## Short-link resolution

Runs in the inspect worker, before any adapter, as step one of `SourceRouter.inspect`.

1. `rate_control.acquire("linkedin", "metadata")`. The worker already binds the transport
   hooks for platform `linkedin`.
2. `transport.head(short_url, follow_redirects=False, deadline=request.deadline)`. That is
   exactly one request, with no cookie header. Response cookies are ignored and no body is
   read.
3. Classify per data-model "ResolutionOutcome". The destination is never contacted during
   resolution.
4. On `resolved`: build a new `InspectInput` with `source_url` set to the query-free
   destination and re-enter routing once. A resolved route can never be `short_link`,
   because its host must be `linkedin.com`.
5. On any failure outcome: raise
   `SourceAdapterError(<category>, stage="inspection", detail=<outcome>)`.

Guarantees:

- Hosts contacted for a short link: `lnkd.in`, then only `linkedin.com`/`www.linkedin.com`
  and the media hosts the normal LinkedIn path already uses (SC-004).
- The public-address policy, TLS hostname pinning, deadline, and 429 handling are the
  transport's usual ones (FR-005).
- A second hop is never followed. A `Location` back on `lnkd.in` is `too_many_redirects`.

## Transport change

`GuardedTransport.head` and `GuardedHTTPTransport.head` gain
`follow_redirects: bool = True`. With `False`, the first response is returned as is,
including a `3xx`, and `TransportResponse.headers["location"]` carries the raw `Location`.
All existing callers keep the default.

## Adapter routing after recognition

| Route | Order | Change |
|---|---|---|
| `post` (any type, any trailing code) | yt-dlp, then `linkedin_image` on `unavailable`/`no_formats` | yt-dlp now also accepts hyphen-code addresses through `OpenMediaLinkedInPostIE` (research R7) |
| `embed` | `linkedin_image` | Unchanged |

`OpenMediaLinkedInPostIE`:

- Subclass of yt-dlp `LinkedInIE`, registered with `add_info_extractor` on every
  `YoutubeDL` the adapter creates. `allowed_extractors` is unchanged.
- `suitable` and `_match_id` delegate to `recognize_source_url` (one source of truth); `_VALID_URL` is only a coarse `linkedin.com/posts/` match.
- `extractor_key` `OpenMediaLinkedInPost` maps to platform `linkedin`.
- The identity check still applies: yt-dlp's `id` must equal the route's `media_id`.

## Worker protocol change

The terminal `error` event may carry `"detail": "<outcome>"`. The parent accepts only
`not_found`, `no_redirect`, `too_many_redirects`, `timed_out`, `outside_linkedin`, and
`not_a_post`. Any other value is ignored. No other field is added.

## Identity handoff to the parent

After a successful inspection of a short-link request, the coordinator:

1. Runs `recognize_source_url(result.metadata.canonical_url)`. The result must be a LinkedIn
   `post` or `embed` route whose `media_id` equals `result.metadata.media_id`. Otherwise
   it raises the existing `WorkflowError`.
2. Rebinds `request.source_url` and `request.media_id` to that route before choices are
   published.

For every other request, the existing check (`result.metadata.media_id == request.media_id`)
is unchanged.

## Amendments to feature 001 contracts

Applied during implementation, each marked "(amended by 004)":

1. `contracts/source-adapters.md`: LinkedIn recognized inputs, as in the table above. Add the
   short-link resolution step and the `follow_redirects` transport parameter.
2. `contracts/source-adapters.md`: the worker `error` event's optional `detail`.
