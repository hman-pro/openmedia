# Music Link Contract

This extends 001 source routing for YouTube Music only.

## Input grammar and normalization

Supported canonical input: `https://music.youtube.com/watch?v=<id>`, with one nonempty `v`
matching `[A-Za-z0-9_-]{6,64}`. Count music hosts in the existing exactly-one-supported-link
rule, including malformed routes so refusals are explained. Retain existing private-chat,
URL-entity, plain-text, scheme-upgrade, punctuation, and credential checks. Add bare music
host recognition consistently. Reject fragments under the current route rule.

| Input shape | Outcome |
| --- | --- |
| Music watch with one valid v | youtube/audio route; music-host canonical URL |
| Music watch with v plus list/index/radio/si/t | Same complete track; all context removed |
| Music watch with repeated v, blank v, malformed v | unsupported_url; no extraction |
| Music playlist or browse album without v | music_collection; ask for a single track |
| Music watch with only list and no v | music_collection; no arbitrary member |
| Music search/artist/home or other path | unsupported_url |
| Regular YouTube watch with list | Existing unsupported_collection behavior |
| Regular YouTube watch without list | Existing video route |
| Lookalike or unrelated host | Not a supported host; never contacted through recognition |

For `/browse/<id>`, album identifiers prefixed `MPREb_` are classified as music collections;
other browse targets remain unsupported pages. `/playlist` is a collection regardless of
query; only `/watch` permits track context. Any repeated v on watch is malformed before
collection classification. Keep the classification deterministic and test it explicitly.

Re-recognizing a canonical music URL must produce the same platform, ID, and route kind.
No context parameters may reach extraction. No additional redirect resolver is introduced;
all actual HTTP follows existing guarded destination checks, not a blanket music redirect rule.
