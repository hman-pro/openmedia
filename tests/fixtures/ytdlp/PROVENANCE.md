# yt-dlp fixture provenance

These are sanitized structural subsets derived from the credential-free T059 inspections
recorded in `specs/001-media-download/validation.md` on 2026-09-16 with yt-dlp 2026.8.19.
Titles and creators are invented, and signed CDN URLs were replaced by `.invalid` URLs.
They preserve extractor keys, native format fields, codec relationships, and size certainty.


`linkedin-video-progressive.json` is the format shape the pinned yt-dlp 2026.8.19 `LinkedIn`
extractor returned for a credential-free public `ugcPost` video during the 2026-09-21 T074
probe: two progressive MP4 renditions whose `vcodec`, `acodec`, dimensions, and sizes are all
null (unknown, not absent), distinguished only by `tbr`. The slug, title, and URLs are
invented; the null fields and bitrates are as observed.
