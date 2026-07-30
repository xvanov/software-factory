# Story

## Title
D012 prove deleted state.yaml regenerates without re-triage

## Slug
`d012-prove-deleted-state-yaml-regenerates-without-re-triage`

## Scope
`test`

## Summary
Add regression coverage that proves direction status persists in the database when `state.yaml` is deleted, that `pm-sync` does not re-triage the direction, and that the projection file is regenerated without changing status.

# Acceptance Criteria

- A direction whose `state.yaml` is deleted keeps its status across a factory restart, and `pm-sync` does not re-triage it.
- `state.yaml` is still written for human inspection, and a test asserts the file can be deleted and regenerated from the database without changing status.

### Testable Claims (EARS)
AC1.1: WHEN a direction's `state.yaml` is deleted and the factory restarts, THE direction status SHALL remain unchanged.
AC1.2: WHEN `pm-sync` runs after a direction's `state.yaml` is deleted, THE system SHALL NOT re-triage that direction.
AC2.1: WHEN a direction status exists in the database and `state.yaml` is missing, THE system SHALL write `state.yaml` for human inspection.
AC2.2: WHEN `state.yaml` is regenerated from the database after deletion, THE regenerated file SHALL preserve the direction's status.

# Tasks / Subtasks

- [x] Identify the existing integration/CLI test location covering direction lifecycle and `pm-sync`
- [x] Add regression test fixture with a direction row present in the database and matching on-disk direction files
- [x] Delete `state.yaml` within the test setup after authoritative DB status exists
- [x] Exercise factory restart or equivalent fresh process/read-path setup
- [x] Run `pm-sync` in the test scenario
- [x] Assert the direction does not return to `created`
- [x] Assert the direction is not re-triaged by `pm-sync`
- [x] Assert `state.yaml` is regenerated after the run
- [x] Assert regenerated `state.yaml` carries the same status as the database row
- [x] Keep assertions scoped to regression behavior; no new product behavior
- [x] Verify test remains stable if run repeatedly

## Dev Notes

### Scope Notes
- This is a test-only regression slice.
- Validate cross-lifecycle behavior spanning deletion, fresh process/read path, `pm-sync`, and projection rewrite.
- Do not introduce new runtime behavior in this story; rely on the backend slices that make DB status authoritative and `state.yaml` best-effort projection.

## flow.md
# Operator flow — adopting database-backed direction status

The operator-visible behaviour of this change. Each step is something a person
does and can observe the result of.

1. **Deploy the change and start a tick.** The operator runs `factory tick --app
   factory`. The tick completes normally; no direction changes status merely
   because the schema grew.

2. **Inspect what would be imported.** The operator runs `factory
   directions-backfill --app factory` (dry-run is the default) and reads a count
   of directions that have no database row yet. Nothing is written.

3. **Import the existing directions.** The operator re-runs the command with
   `--real-run` and sees `imported=<n> skipped=0`. Every direction under
   `apps/factory/directions/` now has a row whose status matches the status that
   was in its `state.yaml`.

4. **Re-run the import.** The operator runs the same command again and sees
   `imported=0 skipped=<n>`. Running it twice changes nothing, so a nervous
   operator can always check rather than guess.

5. **Confirm the database is now authoritative.** The operator deletes one
   direction's `state.yaml`, runs `factory pm-sync --app factory`, and observes
   that the direction is NOT re-triaged and does not reappear as `created` — its
   status survived the file's deletion.

6. **Confirm the file is still there for humans.** The operator looks at the same
   direction's directory and sees `state.yaml` has been rewritten from the
   database, carrying the same status.

7. **Confirm a persona now receives ancestor-story context.** The operator files
   a direction with `parent_direction` pointing at a direction that has already
   shipped, dispatches it, and reads the composed prelude in that story's run
   record: it contains a "Merged Story / Dev Agent Record" section naming the
   parent's deployed story. Before this change that section was always absent.

## api_spec.md
(none)

## Direction Acceptance Criteria (verbatim)
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

## Context Pointers
- No canonical context files were provided in the prelude for this invocation.
- Load implementation context directly from the code paths that currently define:
  - `pm-sync`
  - direction state read/write helpers
  - database-backed direction persistence
  - existing CLI/integration test harness for factory lifecycle commands

## Test Focus
- Prefer an integration-style regression test over a narrow unit test.
- Assert observable operator outcomes from flow steps 5 and 6.
- Use database state as the precondition and deletion of `state.yaml` as the perturbation.
- Ensure the test proves both halves of the requirement:
  - status persistence without file presence
  - file regeneration as projection
- Avoid coupling assertions to incidental audit-log formatting unless required for status preservation proof.

# References

- `stories/0-d012-add-directions-table-schema-and-db-access-skeleton.md`
- `stories/0-d012-read-direction-status-from-db-in-pending-directions.md`
- `stories/0-d012-make-mark-direction-status-write-db-then-project-state-yaml.md`
- `stories/0-d012-add-directions-backfill-cli-with-dry-run-default.md`
- Direction: `D012 persist direction status in database`

# Dev Agent Record

- Status: Completed
- Agent: Amelia (OpenHands)
- Branch: factory/story-128-d012-prove-deleted-state-yaml-regenerates-without-re-triage
- Completion Notes:
  - Added integration regression coverage in `tests/test_pm_sync_dry_run.py` for deleting `state.yaml` after DB status is authoritative.
  - The test proves DB status survives file deletion across a fresh read path, and repeated `pm-sync` runs do not re-triage the direction.
  - The test then regenerates `state.yaml` from the persisted DB status via the production status-write path and asserts status preservation.
  - Refactored test setup to avoid direct test-time DB bootstrap calls (`create_engine`/`create_all`) by using production code plus `sqlite3` assertions.
  - Validation: `uv run pytest tests/test_pm_sync_dry_run.py -k deleted_state_yaml -q` and `uv run pytest -q` both pass.
- File List:
  - tests/test_pm_sync_dry_run.py
  - stories/128-d012-prove-deleted-state-yaml-regenerates-without-re-triage.md

# Senior Developer Review

- Status: Pending
- Reviewer: TBD
- Review Notes:
  - TBD

# Review Follow-ups

- [ ] TBD
