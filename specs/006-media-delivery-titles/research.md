# Research: Media Delivery Titles

## 1. Existing title ownership

**Decision**: Use `DownloadRequest.metadata.title_or_caption`; tolerate missing metadata
at the delivery helper boundary. Keep metadata and worker schemas unchanged.

**Rationale**: `MediaMetadata` already carries optional source text and the registry
binds it during both automatic and selected workflows. Blank strings are rejected by
its constructor, but the pure helper should still accept blank inputs defensively.

**Alternatives considered**: Re-extracting titles adds source calls; using card text
would inherit truncation, fallback text, and status formatting; adding request fields duplicates data.

Evidence: `src/openmedia/models.py`, `coordinator.py`, `sources/__init__.py`, `workers.py`.

## 2. Telegram message labels

**Decision**: Supply `caption`, `filename`, `parse_mode=None`, and no caption entities
to existing video/document calls, preserving uploaded file objects and video hints.

**Rationale**: The existing library supports both labels. The 64-code-point caption
is comfortably below the documented caption capacity. Filenames are upload labels,
not local paths; retain `selected.<extension>` on disk. Do not claim every Telegram
client displays video filenames prominently.

**Alternatives considered**: Separate text messages do not travel with media;
embedded tags change bytes; sendAudio changes the established delivery convention.

Sources: [python-telegram-bot Bot reference](https://docs.python-telegram-bot.org/en/stable/telegram.bot.html),
[Telegram Bot API](https://core.telegram.org/bots/api).

## 3. Unicode truncation

**Decision**: Plan regex==2026.8.31, using its `\X` grapheme matcher. Count Python
string code points, but retain only a whole-cluster prefix fitting 63 points when
truncation is needed, then append `…`. A first cluster larger than the budget yields
only `…`. Do not normalize to NFC/NFKC, which could alter source text and boundary counts.

**Rationale**: Standard slicing can split combining marks, flags, modifiers, and
joined emoji. A Unicode segmentation library avoids maintaining a partial implementation.
Use iterator matching instead of allocating a list of every cluster.

**Alternatives considered**: stdlib re/slicing lacks full cluster segmentation;
custom combining/ZWJ logic misses Unicode boundary rules; ICU is broader than needed.

The selected release supports Python >=3.10, lists Python 3.13, and declares
Apache-2.0 AND CNRI-Python licensing. These permissive terms can coexist with this
MIT project subject to retaining required third-party notices. Verify wheel installation
and notices in the implementation/container checks; no packages installed in this phase.

Source: [regex 2026.8.31 documentation and metadata](https://pypi.org/project/regex/2026.8.31/).

## 4. Normalization and safe filenames

**Decision**: Normalize Unicode whitespace to ASCII spaces before deleting controls;
remove Cc, Cs, and non-display Cf characters except ZWJ/ZWNJ needed for visible text
and tag characters inside complete emoji flag tag sequences. Preserve a black flag
(U+1F3F4), followed by one or more tag-spec characters (U+E0020–U+E007E), terminated
by CANCEL TAG (U+E007F), as an intact sequence. Remove stray tags, incomplete tag
sequences, and other Cf controls; tags alone must still use the display-empty fallback.
Preserve variation selectors and combining marks. Use the Unicode
`Default_Ignorable_Code_Point` property only to determine whether retained text
has visible content; preserve those characters alongside visible text. Display-empty
input uses `Untitled media`.
Create the filename stem from the full normalized title, independently of caption truncation.
Replace runs of `<>:"/\|?*` with `_`; collapse whitespace and trim outer spaces/dots.
Fallback for a stem consisting only of separators, dots, spaces, or invisible characters.
Prefix `_` for Windows reserved device basenames (CON, PRN, AUX, NUL, COM1–9, LPT1–9,
case-insensitive, including before a dot). Apply the 64-point cluster-safe cap afterward,
also cap the complete filename at 240 UTF-8 bytes including dot, selected extension,
and any ellipsis. If either limit is exceeded, reserve one code point and three UTF-8
bytes for `…`, plus the extension suffix bytes, and retain the longest whole-grapheme
prefix fitting both budgets. Trim trailing stem spaces/dots and append the extension.
A first cluster exceeding either available prefix budget yields only `…` as the stem.

**Rationale**: Saved names should be portable and never express paths. A 240-byte
complete-filename budget leaves headroom for saving on common filesystems, including
when four-byte characters fit the 64-code-point cap. This is an application policy,
not a claim of universal filesystem compatibility. The upload label is never used
as a local file path. Source-title
suffixes are not parsed as format claims; the selected extension is always appended.

**Alternatives considered**: ASCII-only names lose useful titles; using raw title as
a disk path introduces traversal concerns; truncating caption first loses usable filename text.

## 5. Refresh and retry stability

**Decision**: Retain original request metadata throughout download refresh, including
the fallback if no original title exists. Freeze computed labels before Telegram retries.

**Rationale**: Current source refresh updates only the selected transport option and
checks identity. FR-006 permits, but does not require, adopting newly available titles;
retaining the fallback avoids expanding DownloadResult and worker IPC just for optional enrichment.

**Alternatives considered**: Returning refresh metadata across workers adds schema and
identity checks without improving the primary titled-item journey. Never refresh solely for a title.

## Resolution

No unresolved clarification remains. Dependency installation, controlled test results,
container build/startup, and real-client appearance require implementation-time validation.
