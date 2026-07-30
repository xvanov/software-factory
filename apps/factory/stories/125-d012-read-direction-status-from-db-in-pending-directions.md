# Story

## Title
D012 read direction status from DB in pending_directions

## Summary
Change the `pending_directions(app, root, db_path)` read path so direction status resolves from the `directions` table first, then `state.yaml`, then `created`, while preserving the function signature and the returned direction objects.

## Scope
backend

# Acceptance Criteria

- `pending_directions` returns the same directions as before when the database is populated, reading status from the database rather than from `state.yaml`.

### Testable Claims (EARS)
AC1.1: WHEN `pending_directions` is called and a direction has a matching database row, THE function SHALL determine that direction's status from the database row rather than from `state.yaml`
AC1.2: WHEN `pending_directions` is called and the database is populated, THE function SHALL return the same directions as before

# Tasks / Subtasks

- [ ] Identify current `pending_directions(app, root, db_path)` implementation and all direct callers.
- [ ] Update status resolution logic to check the `directions` row first.
- [ ] Preserve fallback order: DB row, then `state.yaml`, then `created`.
- [ ] Preserve function signature and returned object shape.
- [ ] Keep hand-created on-disk directions visible when no DB row exists.
- [ ] Add/adjust unit tests for DB-preferred status resolution.
- [ ] Add/adjust regression tests for fallback to `state.yaml` when no DB row exists.
- [ ] Add/adjust regression tests for fallback to `created` when neither DB row nor `state.yaml` exists.
- [ ] Add/adjust regression tests proving returned direction set matches prior behavior when DB is populated.

# Dev Notes

## Scope constraints
- This story is read-path only.
- Do not change the `pending_directions(app, root, db_path)` signature.
- Do not change returned direction object structure.
- Do not implement the write-path semantics here.
- Do not implement backfill CLI behavior here.
- Do not restore ancestor-story context here.

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

## Acceptance criteria from direction (verbatim)
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

## Direction storage contract excerpts relevant to this story
- `pending_directions(app, root, db_path)` keeps its signature and returns the same objects.
- Status resolution changes to: the `directions` row when one exists, else the on-disk `state.yaml`, else `created`.
- The on-disk fallback is what keeps a direction created by hand between ticks from being invisible.

## Context pointers
- No canonical context files were provided in this invocation.
- Use repository code search to locate the live implementations and tests for:
  - `pending_directions`
  - direction state file parsing/loading
  - database access layer for directions/stories
  - `pm-sync` callers that depend on pending-direction semantics
- If canonical context files are created by an earlier onboarding pass before implementation starts, load only those that exist.

## Implementation notes for Dev/Test handoff
- Primary behavioral delta is status source precedence, not direction discovery.
- Preserve prior filtering/order semantics unless existing tests explicitly show otherwise.
- Add regression coverage for mixed populations: DB-backed directions and file-only directions in the same app.
- Verify behavior when `db_path` is absent or unusable matches existing non-DB fallback expectations already established by current code/tests.
- This story depends on the schema/access skeleton slice existing or being stubbed in test fixtures.

# References

- Direction: D012 persist direction status in database
- Tracker: D012 persist direction status in database
- Related child story: D012 add directions table schema and DB access skeleton
- Related child story: D012 make mark_direction_status write DB then project state.yaml
- Related child story: D012 add directions-backfill CLI with dry-run default
- Related child story: D012 prove deleted state.yaml regenerates without re-triage
- Related child story: D012 restore ancestor deployed-story context via directions DB

# Dev Agent Record

## Agent Model Used
- TBD

## Debug Log References
- TBD

## Completion Notes List
- TBD

## File List
- TBD

# Senior Developer Review

- TBD

# Review Follow-ups

- TBD
