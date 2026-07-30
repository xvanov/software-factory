# Story

## Title
D012 restore ancestor deployed-story context via directions DB

## Slug
`d012-restore-ancestor-deployed-story-context-via-directions`

## Scope
`backend`

## Acceptance Criteria

### Verbatim Acceptance Criteria
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

### Story-Scoped Interpretation
- This story implements the `compose_context_prelude` database-backed ancestor-story lookup described in AC5.
- This story may depend on prior storage work that provides `directions` rows and `stories.direction_id` linkage, but it does not redefine those earlier slices.
- This story must preserve current behavior when `db_path` is omitted or when no deployed ancestor stories are found.

### Testable Claims (EARS)
AC1.1: WHEN evaluating this story in isolation, THE requirement is dependency context for ancestor lookup and not independently testable within this story's scope
AC2.1: WHEN evaluating this story in isolation, THE requirement targets `pending_directions` and is not independently testable within this story's scope
AC3.1: WHEN evaluating this story in isolation, THE requirement targets deletion/regeneration status persistence and is not independently testable within this story's scope
AC4.1: WHEN evaluating this story in isolation, THE requirement targets the backfill CLI and is not independently testable within this story's scope
AC5.1: WHEN `compose_context_prelude` is called with `db_path` supplied, GIVEN an ancestor direction has at least one deployed story resolved through `stories.direction_id`, THE system SHALL append a "Merged Story / Dev Agent Record" section for that ancestor direction
AC5.2: WHEN `compose_context_prelude` is called with `db_path` supplied, GIVEN an ancestor direction has no deployed story resolved through the database, THE system SHALL omit the "Merged Story / Dev Agent Record" section for that ancestor direction
AC5.3: WHEN `compose_context_prelude` is called without `db_path`, THE system SHALL append nothing for database-backed ancestor-story context
AC6.1: WHEN evaluating this story in isolation, THE requirement targets `state.yaml` regeneration behavior and is not independently testable within this story's scope

## Tasks / Subtasks
- [ ] Identify current `compose_context_prelude` call sites and signature constraints
- [ ] Add optional `db_path` parameter without breaking existing callers
- [ ] Implement ancestor direction lookup path gated on `db_path` presence
- [ ] Query deployed stories through `stories.direction_id`
- [ ] Read each selected story's `story_file_path`
- [ ] Reuse existing merged section formatting for "Merged Story / Dev Agent Record"
- [ ] Append merged section only when at least one deployed story exists for the ancestor direction
- [ ] Preserve current no-op behavior when `db_path` is absent
- [ ] Preserve current no-op behavior when ancestor direction has no deployed stories
- [ ] Add focused tests for positive append behavior
- [ ] Add focused tests for omit behavior with no deployed stories
- [ ] Add focused tests for omit behavior with no `db_path`
- [ ] Confirm ancestor resolution is database-driven, not filename-derived

## Dev Notes

### Flow
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

### API Spec
(none)

### Direction Acceptance Criteria (verbatim)
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

### Storage contract excerpts relevant to this story
- `compose_context_prelude` gains an optional `db_path`.
- When supplied, for each ancestor direction it selects that direction's stories in state `deployed` via `stories.direction_id`, reads each one's `story_file_path`, and appends the existing "Merged Story / Dev Agent Record" section.
- With no `db_path`, or no deployed story, it appends nothing — the current behaviour.
- Nothing in a story file's name identifies its direction — only `stories.direction_id` does.

### Context pointers
- No canonical context files were provided in this invocation.
- Use repository code search to locate:
  - `compose_context_prelude`
  - `stories.direction_id`
  - `story_file_path`
  - existing "Merged Story / Dev Agent Record" formatting logic
  - ancestor direction / `parent_direction` resolution path
- If context files are created by earlier chain steps before implementation, load only those that actually exist.

### Implementation guardrails
- Do not infer direction linkage from story filenames.
- Do not change behavior for callers that omit `db_path`.
- Reuse existing merged-section content shape; do not invent a new heading or payload format.
- Restrict story selection to deployed stories for the ancestor direction.
- If multiple deployed stories exist, append using the documented existing merge behavior rather than collapsing to a single arbitrary file.

## References
- Tracker: `D012 persist direction status in database`
- Direction section: `### Ancestor-story context`
- Direction section: `## Acceptance Criteria`
- Direction section: `## Storage contract`
- Flow step: `7. Confirm a persona now receives ancestor-story context.`

## Dev Agent Record
- Status: Not started
- Agent: TBD
- Branch: TBD
- Notes: TBD

## Senior Developer Review
- Status: Pending
- Reviewer: TBD
- Review notes: TBD

## Review Follow-ups
- None yet
