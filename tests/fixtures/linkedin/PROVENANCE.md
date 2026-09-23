# LinkedIn fixture provenance

The fixture shape was captured anonymously from LinkedIn's public embed endpoint on
2026-09-16 for activity `7505650038253965312`, as recorded in `validation.md`. The guest
page used `img.lazy-load.w-full.object-cover.object-center` plus `data-delayed-url` for the
explicit `media.licdn.com` feed attachment; reaction images used `static.licdn.com`.
Signed media URLs, author text, and caption text were replaced with `.invalid` values.

On 2026-09-17 the same embed was re-fetched anonymously to record the metadata element shape
for T085. The post author is the text of
`a[data-tracking-control-name="public_post_embed_feed-actor-name"]`, and the caption is the
text of `p[data-test-id="main-feed-activity-embed-card__commentary"]`, which may contain
`<br>` and nested links. `linkedin-image-single.html` keeps those two elements with their
attributes; the author name, profile URL, aria-label name, and caption were replaced with
`Sanitized …` placeholders. The live page parsed to one attachment plus both fields.


## `linkedin-video-post-hyphen-code.html`

The shape follows the live public post
`https://www.linkedin.com/posts/…-ugcPost-7508434034927017984-lwx-/`, fetched anonymously on
2026-09-23 (research R7). That page carried an `og:title`, a `<title>`, and one `<video>`
whose `data-sources` attribute holds a JSON list of MP4 sources with `src`, `type`, and
`data-bitrate`; yt-dlp's `LinkedInIE._real_extract` reads exactly those. The content is
synthetic: the title is `Sample post`, the two sources point at `media.example.invalid`,
and no author, post text, or media URL was copied from the live page.
