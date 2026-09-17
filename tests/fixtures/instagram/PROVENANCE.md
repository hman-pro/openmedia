# Instagram fixture provenance

`instagram-image-single-post.json` was captured anonymously with Instaloader 4.15.3 on
2026-09-16 from public shortcode `gbStjFIaB4`. The live response reported `GraphImage`,
`mediacount=1`, and a Helsinki Instagram CDN host. A 16-byte range probe returned HTTP 206,
`image/jpeg`, and JPEG/JFIF signature `ffd8ffe000104a4649460001`. The caption/owner were
replaced and the signed primary/thumbnail URLs were replaced with `.invalid` placeholders.

The two sidecar shapes correspond to the anonymous T059 checks documented in
`specs/001-media-download/validation.md`; those captures observed both JPEG and WebP CDN
responses. Signed URLs and personal metadata are omitted.
