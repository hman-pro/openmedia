# Validation Record: Diagnostic Log File

Run on 2026-09-21 on macOS (Darwin 25.6.0), Python 3.13, Docker 29.8.0, branch
`002-file-logging`. Every command used a syntactically shaped fake token; `.env` was not read.

| Quickstart | Result | Evidence |
|---|---|---|
| §1 controlled tests | Passed | 72 new tests pass; full suite 341 passed, 1 deselected (live). Baseline before the feature: 269 passed |
| §2 local trace by hand | **Partly run** | `--check-config` with the flag on: exit 0, directory created `0700` and left empty. Two `run_with_diagnostics` runs wrote one `openmedia-2026-09-21.log` (`0600`) with `startup`/`shutdown` pairs and zero token occurrences. **Not run**: sending real links to a live bot, which needs a real token and Telegram account |
| §3 flag off leaves nothing | Passed | `--check-config` exit 0, `diagnostic_log=off`, directory absent afterwards |
| §4 bad location rejected | Passed | `/proc/nope` → exit 2, `OPENMEDIA_DIAGNOSTIC_LOG_DIR /proc/nope is not writable: OSError: Read-only file system`. A directory inside `OPENMEDIA_WORK_DIR` → exit 2, `must be outside OPENMEDIA_WORK_DIR` |
| §5 container persistence | **Passed with a substitution** | Image built. `--read-only`, `--network none`, named volume at `/var/log/openmedia`: `--check-config` exit 0; two separate containers appended to one day file owned by `10001:10001`, mode `0600`, 2 `startup` and 2 `shutdown` entries, zero token occurrences. Flag on with no volume → exit 2 (read-only file system). **Substitution**: the runs called `run_with_diagnostics` with a no-op instead of polling Telegram, so `docker restart` of a live polling bot with a real token was not exercised |

## Success criteria

| Criterion | Proof |
|---|---|
| SC-002 stage coverage | `tests/integration/test_diagnostic_trace.py`: success, worker failure, inspection timeout, selection expiry, refused admission |
| SC-003 survives restart | `test_a_restart_appends_to_the_same_day`, `test_two_runs_share_one_day_file_with_lifecycle_entries`, container check above |
| SC-004 bounded storage | `test_writing_three_times_the_limit_stays_under_it`, asserted after every write |
| SC-005 token never written | `test_token_never_appears`; `grep -c` of the token in real files: 0 |
| SC-006 log failure is harmless | `test_an_unwritable_log_never_changes_a_request_outcome`, `test_unwritable_directory_never_raises_and_notices_once` |
| SC-007 no added delay | `test_a_full_queue_drops_without_blocking_and_reports_the_count`: five emits against a stalled writer return in under 0.5 s. An end-to-end 5% timing comparison against live sources was **not run** |
| SC-008 flag off leaves nothing | `test_flag_off_full_flow_leaves_no_files`, `test_flag_off_check_config_creates_nothing`, §3 |
| SC-009 entry in the right day file | `test_each_entry_lands_in_the_file_for_its_own_utc_date` |
| SC-001 trace in under 2 minutes | Not measured; it is an operator task. The README commands find a failing request with two `jq` calls |

## Limitations

- The `acknowledgment`, `preview`, `delivery`, and `terminal` stages come from feature 001's
  `observe()` and reach the file through the root logger. That path is unit-tested with a
  synthetic record, not through a full `RuntimeCallbacks` journey with the fake Telegram
  transport.
- The unwritable-directory tests rely on POSIX permissions and would not fail as intended if
  the suite ran as root.
