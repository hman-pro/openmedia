# Data Model: Media Delivery Titles

## Existing entities

`MediaMetadata.title_or_caption: str | None` remains the authoritative optional source
title. `DownloadRequest.metadata` binds that metadata to its request and media identity.
No new persistent field, registry map, serialization field, or adapter contract is required.

`DownloadResult` continues to describe validated output bytes, identity, format, and
measured media hints. It does not carry display titles.

## Derived delivery labels

A pure helper in `media_titles.py` returns an immutable pair of `caption: str` and
`filename: str` from `title: str | None` and validated `extension: str`.

| Value | Validation |
|---|---|
| Normalized title | One line, whitespace collapsed, non-display controls removed, Unicode text preserved; neutral fallback when display-empty |
| Caption | At most 64 code points; truncated only at grapheme boundaries, terminal ellipsis included in budget |
| Safe stem | Derived independently from full normalized title; unsafe runs replaced, reserved names protected, at most 64 code points |
| Filename | Safe stem plus dot and selected extension; extension outside stem budget; at most 240 UTF-8 bytes for the complete filename, including any ellipsis; upload label only |

The helper owns constants for code-point limit 64, complete-filename UTF-8 byte
limit 240, and fallback `Untitled media`. Its values
must not be added to diagnostic events or exception messages.

## Lifecycle

1. Inspection binds source metadata to the admitted request.
2. Existing selection or automatic claim binds the chosen format.
3. Download may refresh expiring transport URLs without changing original title metadata.
4. Delivery validates identity/file boundaries and derives labels once before its retry loop.
5. Every permitted RetryAfter retry uses the same pair. Ambiguous sends retain existing behavior.
6. Existing request eviction and cleanup release metadata and temporary files.

No lifecycle transitions change. Two requests with identical titles remain independent;
filename uniqueness is not required because labels never determine disk paths.
