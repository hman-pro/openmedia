# Choice Policy Contract

The pure function between source inspection and the Telegram card. It has no I/O, no
Telegram types, and no clock, so it is tested with plain `FormatOption` fixtures.

## Signature

```text
choose(options: Sequence[FormatOption], *, media_kind: MediaKind, max_file_bytes: int) -> ChoiceSet
```

- Input `options` is the full adapter result after `SourceRouter.inspect` size exclusion.
- Output fields are defined in `../data-model.md` (ChoiceSet).

## Guarantees

1. Output options are a subset of input options with only `option_id` changed.
2. At most one option per kind; order `video`, `silent`, `audio`; ids 0..n-1.
3. `video`/`silent` are MP4 with H.264 video (and AAC audio for `video`). Codec families are
   read from `transport_ref["vcodec"|"acodec"]` using the same family mapping as the merge
   step; an option without codec information is not phone-playable.
4. Selection order follows research R2 (size filter, shorter-side tier, tie-breaks) and R3.
5. `media_kind=image` returns the single image option with `automatic=true`, or an empty set.
6. Deterministic: the same input gives the same output.
7. Never raises for an empty or all-excluded input; it returns an empty set with `missing`
   filled.

## Required test cases (unit, `tests/unit/test_choices.py`)

| Case | Expect |
|---|---|
| YouTube-like: avc1 144–1080p video-only, 18 muxed, m4a 140, opus 251, merges | `video` = 720p merge; `silent` = 720p avc1; `audio` = 251 |
| Vertical 720×1280 avc1 | Tier 1 (shorter side 720) |
| Only 1080p avc1 and 1440p avc1 | `video` = 1080p (smallest in tier 2) |
| 720p merge estimated 60 MB, 480p fits | `video` = 480p |
| Only VP9/AV1 video | no `video`/`silent`; `missing` = `not_offered` |
| All video candidates over the limit | `missing` = `too_large` |
| LinkedIn-like: one muxed H.264/AAC MP4 | only `video`, `automatic=true` |
| Silent source (video-only avc1, no audio) | only `silent`, `automatic=true` |
| Image | one image option, `automatic=true` |
| Unknown sizes only | unknown-size candidates used; known-size candidates preferred when present |
