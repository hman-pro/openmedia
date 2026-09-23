# Data Model: Diagnostic Log File

Nothing here is application state. No code reads these files back at runtime.
Decisions referenced as §N are in [research.md](research.md).

## Log Settings

Added to `Settings` in `src/openmedia/config.py`. Read once at start.

| Field | Source | Default | Validation |
|---|---|---|---|
| `diagnostic_log` | `OPENMEDIA_DIAGNOSTIC_LOG` | `False` | Exactly `0` or `1`; anything else is a `ConfigError` |
| `diagnostic_log_dir` | `OPENMEDIA_DIAGNOSTIC_LOG_DIR` | `/var/log/openmedia` | Flag on only: absolute, no NUL, not equal to or inside `work_dir` |
| `diagnostic_log_level` | `OPENMEDIA_DIAGNOSTIC_LOG_LEVEL` | `DEBUG` | Flag on only: `CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG` |

Fixed constants, not settings:

| Constant | Value | Requirement |
|---|---|---|
| `DIAGNOSTIC_LOG_MAX_DAYS` | 14 | FR-010 |
| `DIAGNOSTIC_LOG_MAX_BYTES` | 50,000,000 | FR-010 |
| `DIAGNOSTIC_ENTRY_MAX_BYTES` | 65,536 | FR-017 |
| `DIAGNOSTIC_QUEUE_RECORDS` | 10,000 | FR-011 |
| `DIAGNOSTIC_REOPEN_SECONDS` | 60 | FR-011 |

## Day File

- **Name**: `openmedia-YYYY-MM-DD.log`, the UTC date of the entries inside.
- **Location**: directly inside `diagnostic_log_dir`. No subdirectories.
- **Permissions**: directory `0700`, file `0600`.
- **Lifecycle**: created on the first entry of its day → appended to, including after
  restarts → closed when a later day's entry arrives → removed whole by retention.
- **Invariants**: every entry's `ts` date equals the date in the file name. The file ends
  in a newline after every completed write. Retention never trims inside a file and never
  removes today's file.

## Log Entry

One JSON object per line. Keys appear in this order; absent keys are omitted, not null.

| Key | Type | Present | Notes |
|---|---|---|---|
| `ts` | string | always | RFC 3339 UTC, millisecond precision, `Z` suffix |
| `level` | string | always | `DEBUG` … `CRITICAL` |
| `origin` | string | always | `request`, `lifecycle`, `sweep`, `library`; (amended by 004) `input` for `refused` |
| `stage` | string | always | See stage table |
| `request_id` | string | request entries | 32 hex characters, from `REQUEST_CONTEXT` or the request |
| `msg` | string | optional | Free text; URL- and token-redacted |
| `platform` | string | request entries | Source name |
| `elapsed_seconds` | number | request entries | Since request creation, 4 decimals |
| `source_url` | string | `received` only | Submitted link; token-redacted only (§6) |
| `chat_id`, `user_id` | integer | `received` only | Telegram identifiers (§6) |
| `option_id` | integer | `selection` onward | Never a URL or path |
| `outcome` | string | result stages | Existing `DeliveryStatus` values |
| `error_category` | string | failures | Existing category values |
| `failed_stage` | string | failures | Existing values |
| `deadline` | string | deadline expiry | `inspection`, `selection`, `processing`, `cleanup` |
| `deadline_seconds` | number | deadline expiry | The configured value: 60, 900, 600 |
| `error` | string | failures | Full formatted exception chain; redacted |
| `worker_output` | string | worker failure | Sanitized stderr capture (§7) |
| `bytes` | integer | download, delivery | File size, never content |
| `dropped` | integer | after queue overflow | Records dropped since the last written entry |
| `truncated` | boolean | when cut | Entry exceeded `DIAGNOSTIC_ENTRY_MAX_BYTES` |
| `options` | integer | `inspection_finished` | Number of format options found |
| `choices` | array of string | `inspection_finished` | (amended by 003) Kept choice kinds in order, e.g. `["video","audio"]`; empty when none; see `specs/003-streamlined-bot-ux/data-model.md` |
| `automatic` | boolean | `selection` | (amended by 003) True when no tap was needed (one choice or a picture) |
| `progress` | object | `worker_progress` (DEBUG) | Scalar fields of one worker protocol message |
| `settings` | object | `startup` | Effective `Settings` without `telegram_bot_token` |
| `reason` | string | `shutdown`, `refused` | `signal` or `error`; (amended by 004) on `refused`: `not_private`, `no_link`, `unsupported_link`, `too_many_links`, `unsupported_url`, `unsupported_collection` |
| `links` | array of string | `refused` | (amended by 004) Raw link candidates, at most 5, each at most 2,048 characters; not URL-redacted |
| `resolution` | string | `inspection_finished`, short link | (amended by 004) Resolution outcome, e.g. `resolved`, `not_found` |
| `resolved_url` | string | `inspection_finished` (ok), short link | (amended by 004) Query-free resolved post address; not URL-redacted |
| `expired`, `cleanup_retried`, `cleanup_failed`, `swept` | integer | `sweep` | Counts from one maintenance pass |
| `lost` | integer | `log_recovered` | Entries not written while the handler was degraded |

**Validation rules**

- The serialized line, including newline, is at most `DIAGNOSTIC_ENTRY_MAX_BYTES`. Over
  that, `error` then `worker_output` then `msg` are cut, and `truncated` is set. The result
  is still valid JSON.
- The bot token and the `\d{6,}:[A-Za-z0-9_-]+` pattern never appear in any value.
- Names, usernames, phone numbers, and message text other than the link are never fields.

## Stages

Existing names are unchanged so feature 001's timing audit keeps parsing the console.

| Stage | Origin | New | Logger |
|---|---|---|---|
| `received` | request | yes | `openmedia.diagnostic` |
| `rejected` | request | yes | `openmedia.diagnostic` |
| `acknowledgment` | request | no | `openmedia` |
| `inspection_started`, `inspection_finished` | request | yes | `openmedia.diagnostic` |
| `source_response` | request | no | `openmedia` |
| `preview` | request | no | `openmedia` |
| `selection` | request | yes | `openmedia.diagnostic` |
| `download_started`, `download_finished` | request | yes | `openmedia.diagnostic` |
| `send_started` | request | yes | `openmedia.diagnostic` |
| `delivery` | request | no | `openmedia` |
| `telegram_response` | request | no | `openmedia` |
| `cleanup` | request | yes | `openmedia.diagnostic` |
| `expired` | request | yes | `openmedia.diagnostic` |
| `terminal` | request | no | `openmedia` |
| `worker_progress` (DEBUG) | request | yes | `openmedia.diagnostic` |
| `startup`, `shutdown`, `crash` | lifecycle | yes | `openmedia.diagnostic` |
| `sweep` | sweep | yes | `openmedia.diagnostic` |
| `log_recovered` | lifecycle | yes | `openmedia.diagnostic` |
| `refused` (amended by 004) | input | yes | `openmedia.diagnostic` |

(amended by 004) The `refused`, `links`, `resolution`, and `resolved_url` additions are defined in
[data-model.md (004)](../004-linkedin-share-links/data-model.md#refusal-record-new-diagnostic-entry).

`startup` carries the effective settings without the token. `shutdown` carries the reason
(`signal`, `error`). `crash` carries `error`.

## Request Trace

All entries sharing one `request_id`, ordered by `ts`, possibly across two day files. It is
a query, not stored data:

```sh
grep -h <request_id> openmedia-*.log | jq -c .
```

## Handler state (in memory only)

| State | Transition |
|---|---|
| `closed` | first record → `open(day)` |
| `open(day)` | record with later UTC date → close, run retention, `open(new day)` |
| `open(day)` | today's file reaches `DIAGNOSTIC_LOG_MAX_BYTES` → `paused(day)`, one console line |
| `paused(day)` | record with later UTC date → run retention, `open(new day)` |
| any | write or open raises `OSError` → `degraded`, one console line |
| `degraded` | next record at least 60 s later → retry open; success → `open(day)`, `log_recovered` entry, one console line |
