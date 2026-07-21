# Story

## Title
Provide UX auditor runtime inputs — broad read

## Slug
`provide-ux-auditor-runtime-inputs-broad-read-alt-b`

## Scope
`backend`

## Acceptance Criteria
- [x] Scheduled UX audit input includes at least one flow.md plus app URL/runtime context.
- [x] UX auditor can reference concrete flow filenames and step numbers from supplied artifacts.

### Testable Claims (EARS)
AC1.1: WHEN scheduled UX audit input is assembled, THE scheduled UX audit input SHALL include at least one `flow.md`.
AC1.2: WHEN scheduled UX audit input is assembled, THE scheduled UX audit input SHALL include app URL/runtime context.
AC2.1: WHEN the UX auditor produces references from supplied artifacts, THE UX auditor SHALL reference concrete flow filenames.
AC2.2: WHEN the UX auditor produces references from supplied artifacts, THE UX auditor SHALL reference step numbers.

## Tasks / Subtasks
- [x] Inspect scheduler and UX audit input-builder entrypoints.
- [x] Identify current scheduled UX audit payload contract.
- [x] Define runtime input shape carrying flow artifact(s).
- [x] Define runtime input shape carrying app URL/runtime context.
- [x] Ensure payload requires at least one `flow.md` artifact for scheduled UX audits.
- [x] Persist or forward artifact filename metadata intact.
- [x] Persist or forward step structure intact for downstream citation.
- [x] Update scheduled UX audit builder path only.
- [x] Avoid broad auditor behavior changes beyond input consumption needed for citation.
- [x] Add backend tests for scheduled payload inclusion of `flow.md`.
- [x] Add backend tests for scheduled payload inclusion of app URL/runtime context.
- [x] Add backend tests proving filename metadata survives transport.
- [x] Add backend tests proving step-number metadata survives transport.
- [x] Document discovered implementation file paths in Dev Agent Record.

## Dev Notes
- No canonical context files were provided in this run (`context/project.md`, `context/navigation.md`, module files unavailable).
- Build context from repository code during implementation; record actual source file pointers in Dev Agent Record for downstream personas.
- This story is scoped broadly across the backend path needed to make the acceptance criteria true, but implementation sequence should still honor PM decomposition: input plumbing first, citation behavior second where minimally necessary to satisfy the broad-read story.
- Because `flow.md` sibling artifact is absent in the direction, include the required marker below.
- Because `api_spec.md` sibling artifact is absent in the direction, include the required marker below.
- No explicit repo-level current-state references are available; reviewer should treat any unrecorded path assumptions as defects.

### flow.md
(none)

### api_spec.md
(none)

### Direction Acceptance Criteria (verbatim)
- [x] Scheduled UX audit input includes at least one flow.md plus app URL/runtime context.
- [x] UX auditor can reference concrete flow filenames and step numbers from supplied artifacts.

## References
- Direction: `D009 provide-ux-auditor-runtime-inputs`
- PM tracker title: `D009 provide-ux-auditor-runtime-inputs`
- PM child story context: `D009 attach flow.md and app runtime context to scheduled UX audits`
- PM child story context: `D009 make UX auditor cite flow filenames and step numbers`

## Dev Agent Record
- Status: Completed
- Implementation paths discovered:
  - `factory/chain/scheduled_tasks.py` — `_build_ux_auditor_context`, `_collect_flow_artifacts`, `_live_run`, `_file_finding_as_direction`, `run_scheduled_persona`
  - `factory/personas/ux_auditor.md` — UX auditor persona prompt (pre-existing, already requires flow+step citation in output schema)
  - `factory/directions/creator.py` — `create_direction`, `_build_flow_md`
  - `factory/directions/parser.py` — `Direction` dataclass
- Tests added/updated:
  - `tests/test_ux_auditor_input.py` — 5 new tests:
    - `test_multiple_flow_artifact_filenames_all_survive_in_context` (AC2.1 — filename metadata survival)
    - `test_step_numbers_from_flow_artifact_survive_in_context` (AC2.2 — step-number survival)
    - `test_built_context_instructs_ux_auditor_to_cite_filenames_and_steps` (AC2.1+AC2.2 — citation instruction presence)
    - `test_filename_and_step_metadata_survive_full_live_run_transport` (AC2.1+AC2.2 — end-to-end transport survival)
    - `test_file_finding_preserves_filename_and_step_for_downstream_citation` (AC2.1+AC2.2 — downstream direction filing preserves metadata)
- Notes:
  - Narrow-read (story 78) already implemented the core input plumbing: `_collect_flow_artifacts`, `_build_ux_auditor_context` with flow artifacts + app URL + runtime context, and the guard requiring at least one flow.md.
  - Broad-read adds: explicit `### Citation Requirements` section in the scheduled UX audit context that instructs the UX auditor to cite flow filenames and step numbers; focused tests proving filename and step-number metadata survive the full transport chain from collection → context → prompt → filed direction.
  - The UX auditor persona prompt (`ux_auditor.md`) already includes citation requirements in its output schema (`flow` and `step` fields), so no persona prompt changes were needed.
  - All existing tests continue to pass; full suite green.

## Senior Developer Review
- Status: Pending
- Reviewer: _TBD_
- Review notes: _TBD_

## Review Follow-ups
- _None yet_