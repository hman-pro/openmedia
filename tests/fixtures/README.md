# Test fixtures

Fixtures here make source behaviour reproducible. They are committed on purpose: the
repository's `.gitignore` excludes media extensions globally and then re-includes
`tests/fixtures/**`, so a sanitized `.mp4` under this directory is versioned while a stray
download elsewhere is not.

## What belongs here

**Sanitized source responses.** Captured `yt-dlp -J` metadata, Instaloader post payloads,
and LinkedIn post HTML, saved as real upstream shapes rather than hand-written
approximations. Unit-made synthetic examples supplement these; per
`contracts/source-adapters.md` they never replace them, because an adapter that only ever
sees our idea of a response will break on the real one.

**Tiny licensed media.** A few seconds and a few kilobytes is enough to exercise byte
preservation, size caps, and document-vs-photo delivery. Every media file needs a licence
that permits redistribution.

## Sanitizing a capture

Real captures carry things that must not be committed:

- **Signed and expiring URLs.** CDN media URLs embed tokens. Replace the query string with
  a stable placeholder; keep the path shape if a test asserts on routing.
- **Personal data.** Replace usernames, display names, user IDs, comments, and profile
  images with invented values. Keep the *shape* — an adapter that reads `owner.username`
  must still find a string there.
- **Credentials of any kind.** Cookies, session IDs, CSRF tokens, `Authorization` headers.
  A capture taken while logged in is not usable here; retake it anonymously, since the
  project only ever supports anonymous access.
- **Private posts.** Only credential-free public examples. If a category cannot be
  represented anonymously, that is a scope decision to escalate, not a fixture to fake.

## Naming and provenance

Name files `<platform>-<media-type>-<case>.<ext>`, for example
`instagram-image-single-post.json` or `linkedin-image-article-preview.html`. Case names
should say what the fixture proves, especially for negative cases — an article preview
image the parser must *not* select is as important as one it must.

Each fixture needs a provenance record in `PROVENANCE.md` alongside it: source platform,
capture date, dependency version used to capture, what was sanitized, and for media the
licence and its source. A fixture whose origin nobody can reconstruct cannot be refreshed
when an upstream changes.

## What does not belong here

Live source examples. Real URLs for the opt-in `live` suite go in a machine-local manifest
outside version control (`OPENMEDIA_LIVE_MANIFEST`), because they age, they identify real
accounts, and they are network-location specific. Only the *example* manifest, filled with
placeholders, is committed.
