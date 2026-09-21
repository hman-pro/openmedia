# Feature Specification: Diagnostic Log File

**Feature Branch**: `002-file-logging`

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: "I would like to add a complete log as file so I can traice the problems."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trace one failed request end to end (Priority: P1)

A person reports that a link did not work. The operator opens the log file, finds that
request, and reads every step the bot took for it in order: link received, inspection,
the options shown, the selection, the download, the send, and the cleanup. The step that
failed is recorded with its cause and the full error detail, so the operator can name the
failing stage without reproducing the problem.

**Why this priority**: This is the reason the feature exists. Today the bot writes a short
summary to the console only, and that output is gone once the process or container is
replaced. Without a durable, complete record there is nothing to trace. The record is a
development aid: the developer switches it on with a feature flag while investigating, and
it stays off otherwise.

**Independent Test**: Submit a link that is known to fail during download, then open the
log file and confirm that every stage of that request appears under one request identifier,
ending in an entry that names the failing stage and the cause.

**Acceptance Scenarios**:

1. **Given** the bot is running with the diagnostic log flag on, **When** a request completes
   successfully, **Then** the log file contains one entry for each stage of that request,
   each with a timestamp, severity, stage name, and the same request identifier.
2. **Given** a request fails at any stage, **When** the operator searches the log file for
   that request identifier, **Then** the entries show the last successful stage, the
   failing stage, the failure category, and the full error detail including the error chain.
3. **Given** a request is stopped by a deadline (inspection, selection expiry,
   download-and-send, or cleanup), **When** the operator reads that request's entries,
   **Then** the entry names which deadline expired and how long the stage had run.
4. **Given** a source worker produced diagnostic output while failing, **When** the
   operator reads that request's entries, **Then** the sanitized worker output is present
   in the log file.

---

### User Story 2 - One file per day that survives restarts and stays bounded (Priority: P2)

The operator restarts or redeploys the bot and can still read what happened before the
restart. Each calendar day has its own file named by its date, so the operator opens the
day a problem happened instead of searching one large file. The log never grows until the
disk is full: whole day files are removed automatically once an age or size limit is reached.

**Why this priority**: A log that disappears on restart misses the crashes that matter most,
and a log that grows without limit turns a diagnostic aid into an outage. Both are needed
before the file can be left switched on.

**Independent Test**: Generate entries, restart the bot, and confirm the earlier entries are
still readable. Then generate entries past the size limit and confirm total log storage stays
under the limit while the newest entries are kept.

**Acceptance Scenarios**:

1. **Given** entries were written before a restart, **When** the bot starts again, **Then**
   those entries are still readable and new entries continue after them.
2. **Given** the bot runs across a day boundary, **When** the first entry of the new day is
   written, **Then** it goes to a new file named for that date and the previous day's file is
   left complete and unchanged.
3. **Given** the bot restarts during a day, **When** it writes again, **Then** entries are
   appended to that day's existing file and nothing is overwritten.
4. **Given** day files exist that are older than the age limit, or total storage passes the
   size limit, **When** the bot starts or a new day begins, **Then** the oldest day files are
   removed first and the current day's file is never removed.
5. **Given** the bot starts, stops, or crashes, **When** the operator reads the log file,
   **Then** the start, the stop reason, and any unhandled error are recorded.

---

### User Story 3 - Control location and detail without code changes (Priority: P3)

The diagnostic log is behind a feature flag that is off by default. The operator turns the
flag on, and chooses where the files are written and how detailed they are, through runtime
configuration. Invalid settings are reported by the existing
configuration check before the bot starts.

**Why this priority**: Defaults cover the common case. Control matters when the operator
moves the deployment or needs more detail for one investigation.

**Independent Test**: Change the log location and detail level, run the configuration check,
start the bot, and confirm entries appear at the new location with the new level of detail.

**Acceptance Scenarios**:

1. **Given** a log location that cannot be written to, **When** the operator runs the
   configuration check, **Then** the check fails with a message naming the location and
   the reason.
2. **Given** the flag is off or not set, **When** the bot runs, **Then** no log file or log
   directory is created, no identifying data is written anywhere, and console output behaves
   as it does today.
3. **Given** the detail level is raised, **When** a request runs, **Then** the log file
   contains the additional detail for that request.

---

### Edge Cases

- The log location becomes unwritable or the disk fills while the bot is running: requests
  MUST keep being served, the problem is reported once on the console, and file logging
  resumes when the location is writable again.
- An error message or worker output contains the bot token: the token MUST be redacted
  before the entry reaches the file.
- Several requests run at the same time: their entries interleave in the file, and each
  entry still carries its own request identifier so one request can be filtered out.
- A single entry is very large, for example a long error chain or worker output: it is
  truncated at a fixed maximum with a marker showing that truncation happened.
- An event happens outside any request, such as startup, shutdown, or the cleanup sweep:
  it is recorded without a request identifier and labeled with its origin.
- A request starts before midnight and finishes after it: its entries are split across two
  day files, and the shared request identifier is what joins them.
- The current day's file alone passes the size limit: writing to the file stops for the rest
  of that day, the condition is reported once on the console, and requests keep being served.
- The flag is changed while the bot is running: the change takes effect at the next start.
- The bot is killed without a clean shutdown: entries written before the kill remain
  readable and the file is not left corrupted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When the diagnostic log flag is on, system MUST write diagnostic entries to
  files that persist across bot restarts and redeployments.
- **FR-018**: The diagnostic log MUST be controlled by a feature flag that is off by default.
  With the flag off, system MUST NOT create any log file or directory and MUST NOT write the
  identifying data of FR-009 anywhere.
- **FR-019**: System MUST write one file per calendar day in UTC, named with that date so
  files sort in date order. Entries MUST go to the file for the day they occur, and a restart
  MUST append to the existing file for that day.
- **FR-002**: System MUST record an entry for every stage of a request: link received,
  inspection start and result, options presented, selection received, download start and
  result, send start and result, cleanup result, and selection expiry.
- **FR-003**: Every entry MUST carry a timestamp with timezone, a severity, the stage or
  origin, and the request identifier when the entry belongs to a request.
- **FR-004**: Failure entries MUST include the failure category, the full error detail, and
  the chain of underlying errors.
- **FR-005**: Entries for a deadline expiry MUST name the deadline and the elapsed time.
- **FR-006**: System MUST record sanitized diagnostic output from source workers in the log
  file when a worker fails.
- **FR-007**: System MUST record process lifecycle events: start with the effective
  non-secret configuration, clean stop with its reason, unhandled errors, and cleanup
  sweep results.
- **FR-008**: System MUST redact the bot token and any other runtime secret from every
  entry before it is written, including inside error detail and worker output.
- **FR-009**: System MUST record the submitted link and the Telegram chat and user
  identifiers in the log file entries for a request, so a failure can be reproduced and
  attributed. Console output MUST keep its current redaction of links. Message text other
  than the link, names, usernames, and phone numbers MUST NOT be written.
- **FR-010**: System MUST remove day files older than a fixed age and MUST keep total log
  storage within a fixed limit by removing the oldest day files first. The current day's
  file MUST NOT be removed; if it alone reaches the limit, file writing stops until the
  next day.
- **FR-011**: A failure to write the log file MUST NOT fail, delay, or cancel a user request.
  The write failure MUST be reported on the console once per occurrence, not once per entry.
- **FR-012**: Operators MUST be able to turn the flag on and off, set the log location, and
  set the detail level through runtime configuration, read at start.
- **FR-013**: When the flag is on, the configuration check MUST reject an unwritable log
  location and an invalid detail level before the bot starts. With the flag off, the log
  location MUST NOT be validated.
- **FR-014**: Each entry MUST be written in a consistent line-based structure that an
  operator can search and filter by request identifier, stage, and severity with ordinary
  text tools.
- **FR-015**: Existing console output MUST remain available, so the container runtime's own
  log collection keeps working.
- **FR-016**: The log files MUST be excluded from version control and from the container
  build context.
- **FR-017**: A single entry MUST be truncated at a fixed maximum size, with a visible
  truncation marker.

### Key Entities

- **Log Entry**: One recorded event. Timestamp, severity, stage or origin, optional request
  identifier, message, optional failure category, optional error detail, optional elapsed
  time.
- **Request Trace**: All log entries that share one request identifier, read in time order.
  It is a view over the log, not separately stored data.
- **Day File**: All entries for one UTC calendar date, named by that date. The unit of
  retention: removed whole, never trimmed.
- **Log Settings**: Feature flag (off by default), location, detail level. Size and age
  limits are fixed values.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For any failed request, the operator identifies the failing stage and its
  cause from the log file alone in under 2 minutes, given the request identifier or the
  approximate time.
- **SC-002**: 100% of request stages listed in FR-002 produce an entry, verified across
  successful, failed, expired, and timed-out requests.
- **SC-003**: 100% of entries recorded before a restart remain readable after the restart.
- **SC-008**: With the flag off, a full test run leaves zero log files and zero directories
  behind.
- **SC-009**: 100% of entries are in the file named for the UTC date of their timestamp,
  verified across a simulated day boundary.
- **SC-004**: Total log storage never exceeds the fixed limit, verified by writing at least
  three times the limit in entries.
- **SC-005**: The bot token appears zero times in the log file after a test run that forces
  the token into error messages and worker output.
- **SC-006**: With the log location made unwritable during a run, 100% of user requests
  complete with the same outcome as when logging works.
- **SC-007**: Enabling the log file adds no delay to request handling that a user can
  notice: end-to-end request time stays within 5% of the time measured with the file off.

## Assumptions

- The reader of the log is the single operator who deploys the bot. No in-chat command,
  web view, or remote access to the log is in scope.
- The log is a development and troubleshooting aid, off by default. When the flag is on it
  records at full detail, because the stated goal is a complete record for tracing problems.
  Production runs with the flag off unless the operator is investigating; a crash that
  happens with the flag off is visible only in console output, as it is today.
- The flag is one on/off runtime setting. No flag service, per-user targeting, or change
  while running is in scope.
- Day boundaries use UTC so file names match entry timestamps on every machine.
- Limits are fixed values in line with the project's other fixed limits: 50 MB total log
  storage and 14 day files maximum age. The planning step may adjust the numbers, not the
  principle that both are bounded.
- The deployment provides a persistent storage location for the log. A single container
  stays a single container; no log shipping service, database, or queue is added.
- The log file is not application state. The rule that request state lives in memory is
  unchanged, and nothing reads the log file back at runtime.
- The log file holds personal data (links and Telegram identifiers). The 14-day age limit
  is the retention rule for it, and the file stays on the operator's own storage.
- Media bytes and file contents are never written to the log. File sizes, format labels,
  and durations are.
- Feature 001's adapter contract says worker output is never forwarded to routine logs.
  This feature treats the diagnostic file as a separate, operator-only destination for the
  sanitized output, and the contract text needs a matching amendment during planning.
- Feature 001's runtime contract says log rotation is handled by the container runtime.
  That stays true for console output; the file manages its own size and age.
- Alerting, metrics, dashboards, and log search tooling are out of scope.
