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
| regex | 2026.8.31 | Apache-2.0 AND CNRI-Python | <https://pypi.org/project/regex/2026.8.31/>; retain installed `regex-2026.8.31.dist-info/licenses/LICENSE.txt` |
| requests | 2.34.2 | Apache-2.0 | <https://github.com/psf/requests/tree/v2.34.2> |
| typing-extensions | 4.16.0 | PSF-2.0 | <https://github.com/python/typing_extensions/tree/4.16.0> |
| urllib3 | 2.8.0 | MIT | <https://github.com/urllib3/urllib3/tree/2.8.0> |
| websockets | 17.1 | BSD-3-Clause | <https://github.com/python-websockets/websockets/tree/17.1> |
| yt-dlp | 2026.8.19 | Unlicense | <https://github.com/yt-dlp/yt-dlp/tree/2026.08.19> |
| yt-dlp-ejs | 0.8.0 | Unlicense AND MIT AND ISC | <https://github.com/yt-dlp/ejs/tree/0.8.0> |

The LGPL/GPL packages above remain separate programs or Python libraries installed unchanged.
Their license texts and corresponding-source requirements must be preserved when the container
is redistributed. Consult the licenses themselves for the complete terms.

The regex distribution credits derivation from CPython 2.6 and 3.1's `re` module,
copyright (c) 1998–2001 Secret Labs AB, under CNRI's Python 1.6 license. Its additions
and alterations use Apache-2.0, with copyright 2020 Matthew Barnett. Preserve the
installed license text and these attribution notices when redistributing regex.

## LinkedIn parser provenance

ShareXtract 0.23.4's Apache-2.0 LinkedIn extractor informed the choice of LinkedIn's public
embed route: <https://github.com/wuaishare/sharextract/tree/v0.23.4>. OpenMedia's parser in
`src/openmedia/sources/linkedin.py` is an independent standard-library implementation; no
ShareXtract source text was copied or adapted, so ShareXtract is not a runtime dependency.

## Feature 008 matching-source closure

Public distribution remains pending the feature 008 acceptance gates. The release
pipeline inventories the **actual final image** on native amd64 and arm64, including
all installed Debian binaries and source versions, Debian `Built-Using` edges, application
Python distributions, the separate system Python/pip environment, and unmanaged tools
and base helpers. The reviewed identities and corresponding acquisition hashes are in
[`release/source-policy.json`](release/source-policy.json); unknown components block
publication. This table does not replace the individual component notices.

Corresponding Debian `.dsc`, original and Debian patch archives are obtained through
APT-authenticated metadata, retaining source versions independently of binary rebuild
suffixes. The exact installed Python sdists come from `uv.lock`; system pip has its own
reviewed sdist. CPython, uv/uvx, Deno, their recipes and embedded sources are retained,
including each locked Rust crate, Rust standard-library source, TypeScript, and V8's
bundled ICU/Chromium source and component notices. The V8 archive supplies ICU 77.1
sources for the separately identified Deno ICU data component. Providing sources and
recipes does not promise bit-for-bit binary reproducibility.

The collector preserves original installed copyright/common-license files and packaged
source notices. Some Rust packages omit a separate license file; their exact archived
Cargo metadata and full source remain unchanged. Reviewed fallback cases supply full,
checksum-pinned standard license texts for an explicitly declared supported license and
record the missing separate notice/provenance. Authors are not inferred to be copyright
holders, and template placeholders are not original copyright notices. The MIT-only
archive audit and actual source-notice findings are recorded in
[`release/notice-review.json`](release/notice-review.json). Unknown expressions, unsupported
exceptions or missing required original notices block coverage.

Before the first image push, the completed canonical `sources-VERSION` GitHub release
must publicly provide `source-manifest.json`, exact per-platform inventories,
`sources-*.tar.gz`, and `notices.tar.gz`. Its URLs and hashes are bound by the signed
final image release manifest. These source materials remain available for distributed
images even when later signing, access or acceptance checks fail. The public verifier
checks every declared source, notice and build material inside the logical parts.

The retained FFmpeg 5.1.9 Debian build was inspected on both native architectures during
feature 008: its effective configuration enables GPL components (`--enable-gpl`, including
libx264/libx265) and does not enable `--enable-nonfree`. Preserve the full FFmpeg and
Debian component license texts and corresponding sources; the application's MIT license
does not relicense those components. Actual final candidate build/source checks and
public availability are recorded separately in feature 008 validation.

The image also carries the reviewed unmanaged and embedded component notice texts at
`/usr/local/share/doc/openmedia/RUNTIME_NOTICES.txt.gz`, generated from the exact
checksum-verified source materials. Read them with
`gzip -dc /usr/local/share/doc/openmedia/RUNTIME_NOTICES.txt.gz` inside the image.
The deterministic compressed file and material provenance are retained in
`release/runtime-notices.txt.gz` and `release/runtime-notices.provenance.json`; the
collector checks the installed file against its reviewed checksum. This supplements
Debian copyright/common-license files and Python dist-info licenses in their original
installed locations. Public notice archives remain mandatory as well.
