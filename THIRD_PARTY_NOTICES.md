# Third-Party Notices

OpenMedia's own source code is released under the MIT License (see [`LICENSE`](LICENSE)).
That license covers this repository's code only, not the components listed here. This file
records the third-party runtime closure and source/notice obligations for the container
defined by the repository. The corresponding license texts remain in the installed Python
distributions and Debian packages. Anyone distributing the image must preserve those texts
and satisfy the copyleft source-availability obligations noted below.

## Runtime tools

| Component | Pinned build | License / distribution note | Source |
|---|---|---|---|
| CPython | 3.13.15, official `python:3.13.15-slim-bookworm` image | PSF-2.0; retain Python notices | <https://github.com/python/cpython/tree/v3.13.15> |
| uv | 0.12.15, official distroless image | MIT OR Apache-2.0 | <https://github.com/astral-sh/uv/tree/0.12.15> |
| Deno | 2.9.6, official `denoland/deno:bin-2.9.6` image | MIT; retain bundled V8 and component notices | <https://github.com/denoland/deno/tree/v2.9.6> |
| FFmpeg | Debian `7:5.1.9-0+deb12u1` | Debian enables `--enable-gpl`; the resulting FFmpeg binaries/libraries are GPL-2.0-or-later. Image distributors must provide corresponding source under GPL terms. `--enable-nonfree` is not used. | <https://sources.debian.org/src/ffmpeg/7%3A5.1.9-0%2Bdeb12u1/> |

FFmpeg is invoked only to combine one local source video stream and one local source audio
stream with `-c copy`. This project does not link against FFmpeg libraries, re-encode media,
or broaden the product's source-format scope. The exact image smoke test records `ffmpeg
-version`; it must continue to show the pinned Debian version and `--enable-gpl` without
`--enable-nonfree` before distribution.

## Locked Python runtime closure

Versions are resolved by `uv.lock`; development-only pytest packages are not installed in the
runtime image.

| Distribution | Version | License | Source / notice |
|---|---:|---|---|
| anyio | 4.15.1 | MIT | <https://github.com/agronholm/anyio/tree/4.15.1> |
| Brotli | 1.2.0 | MIT | <https://github.com/google/brotli> |
| certifi | 2026.7.22 | MPL-2.0 | <https://github.com/certifi/python-certifi> |
| charset-normalizer | 3.5.1 | MIT | <https://github.com/jawah/charset_normalizer/tree/3.5.1> |
| h11 | 0.16.0 | MIT | <https://github.com/python-hyper/h11/tree/v0.16.0> |
| httpcore | 1.0.9 | BSD-3-Clause | <https://github.com/encode/httpcore/tree/1.0.9> |
| httpx | 0.28.1 | BSD-3-Clause | <https://github.com/encode/httpx/tree/0.28.1> |
| idna | 3.19 | BSD-3-Clause | <https://github.com/kjd/idna/tree/v3.19> |
| Instaloader | 4.15.3 | MIT | <https://github.com/instaloader/instaloader/tree/v4.15.3> |
| mutagen | 1.48.1 | GPL-2.0-or-later | <https://github.com/quodlibet/mutagen/tree/release-1.48.1> |
| pycryptodomex | 3.23.0 | BSD-2-Clause and public-domain components | <https://github.com/Legrandin/pycryptodome/tree/v3.23.0> |
| python-telegram-bot | 22.8 | LGPL-3.0-only | <https://github.com/python-telegram-bot/python-telegram-bot/tree/v22.8> |
| requests | 2.34.2 | Apache-2.0 | <https://github.com/psf/requests/tree/v2.34.2> |
| typing-extensions | 4.16.0 | PSF-2.0 | <https://github.com/python/typing_extensions/tree/4.16.0> |
| urllib3 | 2.8.0 | MIT | <https://github.com/urllib3/urllib3/tree/2.8.0> |
| websockets | 17.1 | BSD-3-Clause | <https://github.com/python-websockets/websockets/tree/17.1> |
| yt-dlp | 2026.8.19 | Unlicense | <https://github.com/yt-dlp/yt-dlp/tree/2026.08.19> |
| yt-dlp-ejs | 0.8.0 | Unlicense AND MIT AND ISC | <https://github.com/yt-dlp/ejs/tree/0.8.0> |

The LGPL/GPL packages above remain separate programs or Python libraries installed unchanged.
Their license texts and corresponding-source requirements must be preserved when the container
is redistributed. Consult the licenses themselves for the complete terms.

## LinkedIn parser provenance

ShareXtract 0.23.4's Apache-2.0 LinkedIn extractor informed the choice of LinkedIn's public
embed route: <https://github.com/wuaishare/sharextract/tree/v0.23.4>. OpenMedia's parser in
`src/openmedia/sources/linkedin.py` is an independent standard-library implementation; no
ShareXtract source text was copied or adapted, so ShareXtract is not a runtime dependency.
