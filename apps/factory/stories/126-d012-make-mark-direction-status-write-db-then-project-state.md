# Story

## Title
D012 make mark_direction_status write DB then project state.yaml

## Slug
`d012-make-mark-direction-status-write-db-then-project-state`

## Scope
`backend`

## Acceptance Criteria
- A `directions` table exists with one row per direction, keyed by app and
  direction id, holding at minimum: status, tracker issue number, created-at, and
  the last transition's timestamp and actor.
- `pending_directions` returns the same directions as before when the database
  is populated, reading status from the database rather than from `state.yaml`.
- A direction whose `state.yaml` is deleted keeps its status across a factory
  restart, and `pm-sync` does not re-triage it.
- Every existing on-disk direction is imported into the table by a one-time
  backfill that is safe to run twice and reports how many rows it wrote.
- `compose_context_prelude` includes a "Merged Story / Dev Agent Record" section
  for an ancestor direction that has at least one deployed story, resolved
  through the database, and omits the section when there is none.
- `state.yaml` is still written for human inspection, and a test asserts the file
  can be deleted and regenerated from the database without changing status.

### Testable Claims (EARS)
AC1.1: UNTESTABLE-AS-WRITTEN — this story does not define the full minimum column set or migration verification steps for the `directions` table; verify via the schema story and shared contract in Dev Notes
AC2.1: UNTESTABLE-AS-WRITTEN — this story does not exercise `pending_directions`; verify via the dedicated read-path story and shared contract in Dev Notes
AC3.1: WHEN a direction status has been written to the database and that direction's `state.yaml` is deleted before a factory restart, THE system SHALL keep the direction's status across the restart
AC3.2: WHEN `pm-sync` runs after a direction's `state.yaml` was deleted and the direction status exists in the database, THE system SHALL NOT re-triage that direction
AC4.1: UNTESTABLE-AS-WRITTEN — this story does not implement the one-time backfill command or its reporting; verify via the dedicated backfill story and shared contract in Dev Notes
AC5.1: UNTESTABLE-AS-WRITTEN — this story does not exercise `compose_context_prelude`; verify via the dedicated ancestor-context story and shared contract in Dev Notes
AC6.1: WHEN `mark_direction_status(direction, status, by, details)` succeeds in writing the authoritative database row, THE system SHALL still write `state.yaml` for human inspection
AC6.2: WHEN `state.yaml` has been deleted after an authoritative database write and the relevant regeneration path runs, THE system SHALL regenerate `state.yaml` from the database without changing status

## Tasks / Subtasks
- [ ] Update `mark_direction_status(direction, status, by, details)` to keep its signature unchanged
- [ ] Write direction status transition to the `directions` table as the authoritative step
- [ ] Persist transition fields required by the storage contract: status, tracker issue, created_at, updated_at, updated_by
- [ ] Fail the transition when the database row write fails
- [ ] Project the resulting status to on-disk `state.yaml` after the database write succeeds
- [ ] Preserve existing human-inspection shape of `state.yaml` unless the codebase contract requires exact changes elsewhere
- [ ] Treat `state.yaml` projection failure as best-effort only
- [ ] Ensure file projection failure does not fail the transition result after a successful database write
- [ ] Add/adjust tests for successful DB write + successful file projection
- [ ] Add/adjust tests for successful DB write + failed file projection
- [ ] Add/adjust tests proving persisted status survives deletion of `state.yaml`
- [ ] Add/adjust tests proving regenerated `state.yaml` matches DB-backed status
- [ ] Keep changes isolated from `pending_directions`, backfill CLI, and ancestor-context restoration except for shared helpers already required by this write path

## Dev Notes
### Scope notes
- This story is the write-path slice only.
- Keep `mark_direction_status(direction, status, by, details)` signature unchanged.
- Database write is authoritative.
- `state.yaml` becomes best-effort projection.
- A failure to write the file must NOT fail the transition; a failure to write the row MUST.
- Coordinate with the schema story for table availability; do not redefine schema semantics here beyond consuming the documented contract.

### flow.md
[flow.md: see d012-add-directions-table-schema-and-db-access-skeleton Dev Notes for verbatim embed]

### api_spec.md
(none)

### Context pointers
- No canonical context files were provided in this invocation (`context/project.md`, `context/navigation.md`, module docs, and `context/current-state.md` unavailable).
- Build implementation context from the code locations that currently define:
  - `mark_direction_status(direction, status, by, details)`
  - direction `state.yaml` serialization/projection helpers
  - database connection / repository helpers for direction and story persistence
  - any existing tests covering direction transitions and `pm-sync`

### Direction acceptance criteria (verbatim embed)
- A `directions` table exists with one row per direction, keyed by app and
  direction id, holding at minimum: status, tracker issue number, created-at, and
  the last transition's timestamp and actor.
- `pending_directions` returns the same directions as before when the database
  is populated, reading status from the database rather than from `state.yaml`.
- A direction whose `state.yaml` is deleted keeps its status across a factory
  restart, and `pm-sync` does not re-triage it.
- Every existing on-disk direction is imported into the table by a one-time
  backfill that is safe to run twice and reports how many rows it wrote.
- `compose_context_prelude` includes a "Merged Story / Dev Agent Record" section
  for an ancestor direction that has at least one deployed story, resolved
  through the database, and omits the section when there is none.
- `state.yaml` is still written for human inspection, and a test asserts the file
  can be deleted and regenerated from the database without changing status.

### Storage contract excerpts relevant to this story (verbatim)
`mark_direction_status(direction, status, by, details)` keeps its signature and
becomes a database write plus a best-effort `state.yaml` projection. A failure to
write the file must NOT fail the transition; a failure to write the row MUST.

### Implementation constraints
- No HTTP surface changes.
- `direction.md`, `flow.md`, and `api_spec.md` remain git-authored source of intent.
- Do not move story markdown or direction intent files into the database.
- Preserve current behavior for human-readable on-disk status inspection while demoting it from source-of-truth.
- Prefer transactional or clearly ordered persistence so partial failure semantics are explicit and testable.
- If the code currently appends audit data to `state.yaml`, ensure the database remains the authoritative holder of last transition timestamp/actor required by the storage contract.

### Test design notes for downstream personas
- Required failure-mode coverage:
  - DB write error => transition fails
  - file projection error after DB success => transition succeeds
- Required lifecycle coverage:
  - status written to DB
  - `state.yaml` deleted
  - subsequent sync/restart path observes persisted status rather than `created`
  - projection rewritten from DB without status drift
- Avoid coupling this story's tests to the backfill command; use direct setup fixtures where possible.

## References
- Tracker: `D012 persist direction status in database`
- Story slug: `d012-make-mark-direction-status-write-db-then-project-state`
- Related sibling stories from PM decomposition:
  - `D012 add directions table schema and DB access skeleton`
  - `D012 read direction status from DB in pending_directions`
  - `D012 add directions-backfill CLI with dry-run default`
  - `D012 prove deleted state.yaml regenerates without re-triage`
  - `D012 restore ancestor deployed-story context via directions DB`

## Dev Agent Record
- Status: Not started
- Assigned agent: TBD
- Branch: TBD
- Notes:
  - Implement after or alongside schema availability for `directions`
  - Record exact failure-handling decisions here during implementation

## Senior Developer Review
- Review status: Pending
- Review checklist:
  - Signature unchanged for `mark_direction_status`
  - DB write is authoritative and required
  - File projection is best-effort and non-fatal
  - Tests cover both failure modes
  - No unintended read-path or CLI coupling introduced

## Review Follow-ups
- None yet
