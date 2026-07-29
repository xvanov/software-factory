# Story

## Title
Gate UX audits on available flow artifacts — broad read

## Slug
`gate-ux-audits-on-available-flow-artifacts-broad-read-alt-b`

## Scope
`backend`

## Summary
Implement the backend guard and payload contract for replay-based UX auditing so runs do not proceed without at least one available `flow.md` artifact and, when they do proceed, the invocation payload includes at least one `flow.md` path plus contents.

# Acceptance Criteria

- [ ] UX auditor run is skipped or marked not-applicable when zero flow.md files are available.
- [ ] Invocation payload includes at least one flow.md path and contents before replay-based auditing runs.

### Testable Claims (EARS)
AC1.1: WHEN replay-based UX auditing is requested, GIVEN zero `flow.md` files are available, THE UX auditor run SHALL be skipped or marked not-applicable.
AC2.1: WHEN replay-based UX auditing runs, THE invocation payload SHALL include at least one `flow.md` path.
AC2.2: WHEN replay-based UX auditing runs, THE invocation payload SHALL include contents for at least one `flow.md`.

# Tasks / Subtasks

- [ ] Identify the backend decision point that launches or classifies replay-based UX auditor runs.
- [ ] Implement flow-artifact presence detection for available `flow.md` files in invocation context.
- [ ] Gate replay-based UX auditing when zero `flow.md` files are available.
- [ ] Ensure gated outcome is represented as skipped or not-applicable at the existing run/classification boundary.
- [ ] Update UX audit payload assembly to include at least one `flow.md` artifact path.
- [ ] Update UX audit payload assembly to include corresponding `flow.md` contents.
- [ ] Preserve existing replay-based UX auditing behavior when one or more `flow.md` files are available.
- [ ] Add automated tests for zero-flow gating behavior.
- [ ] Add automated tests proving payload contains at least one `flow.md` path and contents before replay-based auditing runs.
- [ ] Verify no replay-based UX audit executes on the zero-flow path.

# Dev Notes

## Scope Notes
- Broad-read story covers both declared acceptance criteria in one backend slice.
- `flow.md` artifact naming in this direction refers to available flow files in invocation context; implement against the repository's existing artifact discovery and payload-building conventions.
- If the codebase distinguishes between "skip" and "not-applicable", use the status already recognized by the UX auditing pipeline; do not invent a new terminal state unless required by existing architecture.
- If no explicit `flow.md` artifact metadata structure exists, extend the existing invocation payload shape minimally and consistently with current artifact serialization patterns.

## flow.md
[flow.md not provided in direction]

## api_spec.md
[api_spec.md not provided in direction]

## Context Pointers
- No canonical context files were provided in this invocation (`context/project.md`, `context/navigation.md`, module files unavailable).
- Build implementation context from the backend code paths that currently: discover direction sibling artifacts, assemble persona invocation payloads, and trigger/classify UX auditor execution.

## Verbatim Direction Acceptance Criteria
- [ ] UX auditor run is skipped or marked not-applicable when zero flow.md files are available.
- [ ] Invocation payload includes at least one flow.md path and contents before replay-based auditing runs.

# References

- Direction: `D011 gate UX audits on available flow artifacts`
- PM tracker title: `D011 gate UX audits on available flow artifacts`
- PM decomposition context:
  - `D011 skip or mark UX replay audit N/A without flow.md`
  - `D011 include flow.md path and contents in UX audit payload`

# Dev Agent Record

## Implementation Notes
- Pending.

## Files Touched
- Pending.

## Test Evidence
- Pending.

# Senior Developer Review

- Pending.

# Review Follow-ups

- Pending.
