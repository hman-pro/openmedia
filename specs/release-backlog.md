# Remaining release checks

Recorded 2026-10-10. Planned feature implementation is complete; these checks remain
open. The linked feature tasks and validation records remain the authoritative progress
records. Follow-up task IDs below track the same work, not additional features.

- [ ] Verify a public Instagram `GraphImage` single-image inspection and native download
  through the product transport (001 T097). Anonymous operation-scoped cookies are
  already implemented; outstanding work is live evidence.
- [ ] Complete the five-category live source matrix (001 T026/T074), including the
  Instagram image case, and record native formats, bytes, versions and source conditions.
- [ ] Repeat source checks on the deployment network and complete Telegram happy-path,
  two-account isolation, repeated selections and originating-chat delivery (001 T054/T076).
- [ ] Build and run the constrained read-only container; verify startup, polling,
  health, active-work shutdown, child termination and cleanup (001 T053/T075).
  These checks were previously on operator hold. Local-server deployment is now the
  active work requested by the operator; record actual checks as they are performed.
- [ ] Measure 20 eligible inspections and 20 eligible deliveries against the specified
  19/20 timing thresholds and concurrency limits (001 T055/T080).
- [ ] Complete plain/context YouTube Music live-manifest checks (005 T032/T036).
- [ ] Complete the remaining YouTube Music private-chat acceptance matrix: context,
  collections, ordinary-YouTube regression, card progress and byte comparison where
  available (005 T033/T037). Successful track download and phone playback are already
  recorded as partial evidence.
- [ ] Complete YouTube Music container build/startup/health checks (005 T034/T038),
  sharing deployment evidence with the original container checks where applicable.

## Authoritative records

- [Original feature tasks](001-media-download/tasks.md)
- [Original feature validation](001-media-download/validation.md)
- [YouTube Music tasks](005-youtube-music-download/tasks.md)
- [YouTube Music validation](005-youtube-music-download/validation.md)

Latest recorded controlled result: 784 passing tests. No tests or external acceptance
checks were rerun while recording this backlog.

## Local-server deployment — 2026-10-10

- Operator built the image successfully on the local Ubuntu server after correcting
  Dockerfile to copy the packaging-required LICENSE file.
- Operator started the Compose deployment and reported health, stop/restart and
  received-file checks working well. Exact health and shutdown outputs/timing were
  not supplied; full container acceptance tasks remain open for the remaining matrix.
- Supplied console trace shows one confirmed LinkedIn delivery: 7,728,597 bytes,
  6.7273 seconds from request start and 2.8649 seconds from automatic selection.
- Two preceding LinkedIn requests failed during inspection with `unavailable` after
  upstream 4xx responses. Operator believes the posts are public and reports the bot
  described the link as not public. Exact URLs, HTTP statuses and bot wording have
  not been captured here. This needs a separate investigation; no cause is established.

## Separate investigation: public LinkedIn link refused

- [ ] Reproduce the reported public-link refusal on the server with the exact submitted
  link and exact bot response; compare anonymous browser access and product transport.
- [ ] Determine the failing request/status and whether link resolution, source access,
  extraction or user-facing error classification caused the refusal.
- [ ] Fix the demonstrated defect, add controlled regression coverage and revalidate
  through the deployment transport. Do not infer private content from a generic 4xx.

Starting evidence: failed request IDs `dd36e925add9302bd5d0381f1f4deacd` and
`1c71d652e18ebe3a4a5f27406f623ff6`; successful comparison request
`3c43c4d95ff002a2d06d16b53a935ea8`. Diagnostic logging was off.
