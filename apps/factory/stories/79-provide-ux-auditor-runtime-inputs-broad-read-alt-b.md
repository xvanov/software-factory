# Story

## Title
Provide UX auditor runtime inputs — broad read

## Slug
`provide-ux-auditor-runtime-inputs-broad-read-alt-b`

## Scope
`backend`

## Acceptance Criteria
- [ ] Scheduled UX audit input includes at least one flow.md plus app URL/runtime context.
- [ ] UX auditor can reference concrete flow filenames and step numbers from supplied artifacts.

### Testable Claims (EARS)
AC1.1: WHEN scheduled UX audit input is assembled, THE scheduled UX audit input SHALL include at least one `flow.md`.
AC1.2: WHEN scheduled UX audit input is assembled, THE scheduled UX audit input SHALL include app URL/runtime context.
AC2.1: WHEN the UX auditor produces references from supplied artifacts, THE UX auditor SHALL reference concrete flow filenames.
AC2.2: WHEN the UX auditor produces references from supplied artifacts, THE UX auditor SHALL reference step numbers.

## Tasks / Subtasks
- [ ] Inspect scheduler and UX audit input-builder entrypoints.
- [ ] Identify current scheduled UX audit payload contract.
- [ ] Define runtime input shape carrying flow artifact(s).
- [ ] Define runtime input shape carrying app URL/runtime context.
- [ ] Ensure payload requires at least one `flow.md` artifact for scheduled UX audits.
- [ ] Persist or forward artifact filename metadata intact.
- [ ] Persist or forward step structure intact for downstream citation.
- [ ] Update scheduled UX audit builder path only.
- [ ] Avoid broad auditor behavior changes beyond input consumption needed for citation.
- [ ] Add backend tests for scheduled payload inclusion of `flow.md`.
- [ ] Add backend tests for scheduled payload inclusion of app URL/runtime context.
- [ ] Add backend tests proving filename metadata survives transport.
- [ ] Add backend tests proving step-number metadata survives transport.
- [ ] Document discovered implementation file paths in Dev Agent Record.

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
- [ ] Scheduled UX audit input includes at least one flow.md plus app URL/runtime context.
- [ ] UX auditor can reference concrete flow filenames and step numbers from supplied artifacts.

## References
- Direction: `D009 provide-ux-auditor-runtime-inputs`
- PM tracker title: `D009 provide-ux-auditor-runtime-inputs`
- PM child story context: `D009 attach flow.md and app runtime context to scheduled UX audits`
- PM child story context: `D009 make UX auditor cite flow filenames and step numbers`

## Dev Agent Record
- Status: Not started
- Implementation paths discovered: _TBD by Dev_
- Tests added/updated: _TBD by Dev_
- Notes: _TBD by Dev_

## Senior Developer Review
- Status: Pending
- Reviewer: _TBD_
- Review notes: _TBD_

## Review Follow-ups
- _None yet_
