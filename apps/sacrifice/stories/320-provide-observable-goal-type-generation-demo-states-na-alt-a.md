# Story

## Title
Provide observable goal-type generation demo states — narrow read

## Scope
backend

## Summary
Deliver the narrowest backend slice needed to make the UX audit runnable: a deterministic demo fixture and one app-facing runtime path that exposes the documented goal-type generation banner states for frontend/demo consumption, without invoking real background factory work.

# Acceptance Criteria

- [ ] A runnable environment or fixture lets the UX audit observe each documented status-banner state and the final notification-driven return path.

### Testable Claims (EARS)
AC1.1: WHEN the runnable environment or fixture is used for the goal-type generation demo, THE system SHALL let the UX audit observe each documented status-banner state.
AC1.2: WHEN the runnable environment or fixture is used for the goal-type generation demo, THE system SHALL let the UX audit observe the final notification-driven return path.

# Tasks / Subtasks

- [ ] Add deterministic backend fixture state source for goal-type generation demo.
  - [ ] Encode the documented states: `queued`, `in progress`, `pull request open`, `merging`.
  - [ ] Keep state progression deterministic and independent of real background work.
  - [ ] Keep implementation isolated from production generation orchestration.
- [ ] Add one app-facing runtime path that exposes the demo states.
  - [ ] Return fixture-backed state data in a frontend-consumable shape.
  - [ ] Make the path runnable in local audit/demo environments.
  - [ ] Include the final notification-driven return-path state in the exposed demo data.
- [ ] Protect existing runtime behavior.
  - [ ] Ensure normal non-demo generation paths remain unchanged.
  - [ ] Gate demo behavior behind an explicit demo-only trigger/configuration.
- [ ] Add backend tests for deterministic observability.
  - [ ] Verify each documented banner state is reachable/observable through the runtime path.
  - [ ] Verify deterministic ordering/progression semantics as implemented.
  - [ ] Verify the final notification-driven return path is represented in the demo response/fixture.
- [ ] Add minimal operator-facing discoverability for downstream docs handoff.
  - [ ] Record exact backend trigger/path names in code comments or response contract notes suitable for docs follow-up.

# Dev Notes

## Flow embed

# User flow

1. Flow: 010-goal-type-generator/flow.md
2. Step: 6
3. Evidence: The status-banner progression (`queued` → `in progress` → `pull request open` → `merging`) depends on background factory updates, but the provided runtime has no live application endpoint or event stream, so the user-visible transition behavior could not be observed.
4. Suggestion: Expose a deterministic demo or staging flow for goal-type generation status updates so the audit can verify each banner transition and notification handoff.

## API spec embed

(none)

## Direction acceptance criteria embed

- [ ] A runnable environment or fixture lets the UX audit observe each documented status-banner state and the final notification-driven return path.

## Context pointers

- [Source: context/project.md#Identity]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/current-state.md#Goal-type generation]
- [Source: context/current-state.md#Frontend gaps relevant to current work]
- [Source: context/modules/backend.md#FastAPI routes and service patterns]
- [Source: context/modules/backend.md#Testing patterns]
- [Source: context/modules/security.md#Environment and demo-safety expectations]

## Implementation notes

- Narrow-read scope: backend only; do not implement the client rendering or documentation slice in this story.
- PM decomposition context indicates this story should cover the enabling backend fixture plus the minimal observable runtime hook needed for downstream frontend wiring.
- Prefer deterministic fixture/demo data over workers, queues, SSE, websockets, or real long-running orchestration unless already present and trivial to reuse.
- The runtime currently lacks a live application endpoint or event stream for this audit path; this story should close that backend observability gap with the smallest app-facing surface.
- The documented states must appear exactly as provided by the direction evidence unless the existing UI contract requires a stable transport mapping; if mapping is necessary, preserve a clear one-to-one traceability for downstream frontend and test design.
- Because `api_spec.md` is `(none)`, the response contract must be made explicit in implementation/tests.
- If `context/current-state.md` sections named above are absent or renamed in the worktree at execution time, Dev should load the closest matching goal-type generation and frontend-gap sections before coding and note any mismatch in the Dev Agent Record.

# References

- `stories/320-provide-observable-goal-type-generation-demo-states-na-alt-a.md`
- `backend/app/main.py`
- `backend/app/routes/`
- `backend/app/services/`
- `backend/tests/`
- `context/project.md`
- `context/navigation.md`
- `context/current-state.md`
- `context/modules/backend.md`
- `context/modules/security.md`

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
