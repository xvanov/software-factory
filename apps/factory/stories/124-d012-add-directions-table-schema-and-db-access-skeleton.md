# Story

## Title
D012 add directions table schema and DB access skeleton

## Slug
`d012-add-directions-table-schema-and-db-access-skeleton`

## Scope
`backend`

## Acceptance Criteria
1. A `directions` table exists with one row per direction, keyed by app and
   direction id, holding at minimum: status, tracker issue number, created-at, and
   the last transition's timestamp and actor.

### Testable Claims (EARS)
AC1.1: WHEN the application schema is initialized or migrated for this change, THE database SHALL contain a `directions` table.
AC1.2: WHEN a direction row is stored, THE `directions` table SHALL hold one row per direction keyed by app and direction id.
AC1.3: WHEN a direction row exists, THE `directions` table SHALL hold at minimum status, tracker issue number, created-at, and the last transition's timestamp and actor.

## Tasks / Subtasks
- [ ] Add schema definition for `directions` table.
- [ ] Add unique constraint on `(app, direction_id)`.
- [ ] Add index on `(app, status)`.
- [ ] Include documented minimum columns: `app`, `direction_id`, `slug`, `status`, `tracker_issue`, `created_at`, `updated_at`, `updated_by`.
- [ ] Preserve surrogate primary key `id`.
- [ ] Add DB access skeleton for `directions` rows in the existing persistence layer.
- [ ] Add row mapping for documented direction fields.
- [ ] Ensure status values align with current set only.
- [ ] Add tests for schema presence and constraints.
- [ ] Add tests for row round-trip through the DB access skeleton.
- [ ] Do not change HTTP surface.
- [ ] Do not change `pending_directions` behavior in this story.
- [ ] Do not change `mark_direction_status` behavior in this story.
- [ ] Do not implement backfill CLI in this story.
- [ ] Do not implement ancestor-story context restoration in this story.

## Dev Notes
### Scope notes
- This story is the storage-contract foundation only.
- Implement schema and persistence primitives needed by later stories.
- Do not bundle read-path, write-path, CLI, or context-prelude behavior changes here.

### flow.md
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

### api_spec.md
(none)

### Direction acceptance criteria (verbatim)
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

### Storage contract excerpt (verbatim)
### Table: `directions`

| column | type | notes |
|---|---|---|
| `id` | int, pk | surrogate |
| `app` | text, not null | e.g. `factory`, `sacrifice` |
| `direction_id` | text, not null | zero-padded, e.g. `012` |
| `slug` | text, not null | hyphenated slug |
| `status` | text, not null | `created`, `pm-validated`, `needs-direction`, `closed` |
| `tracker_issue` | int, null | GitHub issue for the direction tracker |
| `created_at` | datetime, not null | from the direction's frontmatter |
| `updated_at` | datetime, not null | last transition |
| `updated_by` | text, null | e.g. `factory.chain.pm_sync` |

Unique on `(app, direction_id)`. Index on `(app, status)` — the hot read is
"pending directions for this app".

Statuses are exactly today's set. Do not add a `completed` status: a successful
direction terminates at `pm-validated`, and completion is signalled by its child
stories reaching `deployed`.

### Read path

`pending_directions(app, root, db_path)` keeps its signature and returns the same
objects. Status resolution changes to: the `directions` row when one exists, else
the on-disk `state.yaml`, else `created`. The on-disk fallback is what keeps a
direction created by hand between ticks from being invisible.

### Write path

`mark_direction_status(direction, status, by, details)` keeps its signature and
becomes a database write plus a best-effort `state.yaml` projection. A failure to
write the file must NOT fail the transition; a failure to write the row MUST.

### CLI

```text
factory directions-backfill --app <app> [--dry-run]
```

Imports every on-disk direction that has no row yet. Idempotent. Prints
`imported=<n> skipped=<n>`. `--dry-run` reports without writing, and is the
default, matching the other destructive-ish verbs in this CLI.

### Ancestor-story context

`compose_context_prelude` gains an optional `db_path`. When supplied, for each
ancestor direction it selects that direction's stories in state `deployed` via
`stories.direction_id`, reads each one's `story_file_path`, and appends the
existing "Merged Story / Dev Agent Record" section. With no `db_path`, or no
deployed story, it appends nothing — the current behaviour.

### Context pointers
- No canonical context files were provided in this invocation.
- Use repository code search to locate the existing DB schema/migration entry points, story persistence layer, and any current direction/state readers before implementation.
- If generated during this run by upstream personas, prefer canonical paths only: `[Source: context/project.md]`, `[Source: context/navigation.md]`, `[Source: context/current-state.md#database]`, `[Source: context/modules/<name>.md#persistence]`.

### Implementation constraints
- Keep changes additive and isolated to schema plus persistence primitives.
- Match exact status set: `created`, `pm-validated`, `needs-direction`, `closed`.
- Ensure later stories can consume these primitives without schema churn.
- Preserve current behavior for callers until dedicated follow-on stories land.

## References
- Direction: `D012 persist direction status in database`
- Story file path: `stories/0-d012-add-directions-table-schema-and-db-access-skeleton.md`
- Tracker title: `D012 persist direction status in database`

## Dev Agent Record
- Status: Not started
- Agent: TBD
- Branch: TBD
- Commit(s): TBD
- Notes:
  - TBD

## Senior Developer Review
- Reviewer: TBD
- Review status: Pending
- Checklist:
  - [ ] Schema matches documented storage contract.
  - [ ] Unique key on `(app, direction_id)` verified.
  - [ ] Hot-read index on `(app, status)` verified.
  - [ ] Minimum columns present with expected nullability.
  - [ ] No read/write path behavior bundled beyond persistence skeleton.
  - [ ] Tests cover schema and persistence primitives.

## Review Follow-ups
- None yet.
