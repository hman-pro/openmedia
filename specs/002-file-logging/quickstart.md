# Quickstart and Validation: Diagnostic Log File

Run from the repository root. Contract: [contracts/diagnostic-log.md](contracts/diagnostic-log.md).
Fields and stages: [data-model.md](data-model.md).

## Prerequisites

- `uv sync --locked --group dev`
- `jq` for reading traces
- For the container check only: Docker and a dedicated test bot token

## 1. Controlled validation (no network, no token)

```sh
uv run --locked pytest tests/unit/test_diagnostics.py tests/unit/test_config_diagnostics.py \
  tests/integration/test_diagnostic_trace.py
uv run --locked pytest
```

Expected: all pass, and the full suite still passes, which shows console output did not
change. The new tests must prove:

| Proof | Criterion |
|---|---|
| Success, failure, expiry, and timeout flows each produce every stage in FR-002 under one `request_id` | SC-002 |
| A handler closed and reopened on the same day appends; earlier lines are intact | SC-003 |
| Writing three times the total limit leaves the directory at or under 50,000,000 bytes, newest kept | SC-004 |
| A token forced into a message, an exception chain, and worker output appears zero times in the file | SC-005 |
| With the directory made unwritable mid-run, every request outcome matches the baseline, and stderr gets exactly one notice | SC-006 |
| `emit` returns without blocking while the writer thread is stalled | SC-007 |
| Flag off: the whole run leaves zero files and zero directories under the configured path | SC-008 |
| With an injected clock crossing 00:00 UTC, each entry is in the file named for its `ts` date | SC-009 |
| An oversized entry is valid JSON, within 65,536 bytes, with `truncated: true` | FR-017 |
| A file that ends without a newline gets one before the next entry | Edge case |
| Retention ignores files that do not match the name pattern | §8 |

## 2. Local trace, by hand (about 3 minutes)

```sh
export OPENMEDIA_DIAGNOSTIC_LOG=1
export OPENMEDIA_DIAGNOSTIC_LOG_DIR="$PWD/logs"
uv run python -m openmedia --check-config     # exit 0; logs/ exists and is empty
uv run python -m openmedia                    # send the bot one good link and one bad link
```

In a second terminal:

```sh
f="logs/openmedia-$(date -u +%F).log"
jq -r 'select(.stage=="received") | [.request_id, .source_url] | @tsv' "$f"
grep -h <request_id> logs/openmedia-*.log | jq -c '{ts, stage, outcome, error_category}'
```

Expected: the bad link's trace ends in an `ERROR` entry naming `failed_stage`, with `error`
or `worker_output` present. The console shows no link. `git status` shows nothing under
`logs/`.

## 3. Flag off leaves nothing

```sh
unset OPENMEDIA_DIAGNOSTIC_LOG
rm -rf logs && uv run python -m openmedia --check-config && test ! -e logs && echo clean
```

Expected: `clean`.

## 4. Bad location is rejected before start

```sh
OPENMEDIA_DIAGNOSTIC_LOG=1 OPENMEDIA_DIAGNOSTIC_LOG_DIR=/proc/nope \
  uv run python -m openmedia --check-config; echo "exit=$?"
```

Expected: `exit=2` and a message naming `OPENMEDIA_DIAGNOSTIC_LOG_DIR` and the reason. The
same exit for a directory inside `OPENMEDIA_WORK_DIR`.

## 5. Container persistence

```sh
docker build -t openmedia:dev .
docker run -d --name om --init --read-only --env-file .env \
  -e OPENMEDIA_DIAGNOSTIC_LOG=1 -v openmedia-logs:/var/log/openmedia \
  --tmpfs /tmp:rw,noexec,nosuid,size=536870912,mode=1777 openmedia:dev
docker restart om
docker run --rm -v openmedia-logs:/l alpine sh -c 'grep -c "\"stage\":\"startup\"" /l/openmedia-*.log'
```

Expected: a count of 2 in today's file, one `startup` per run, and a `shutdown` entry with
reason `signal` between them. Record the result and date here when run; a missing Docker or
token means "not run", never "passed".
