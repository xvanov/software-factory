# Story

## Title
Enable UX auditor flow replay inputs — broad read

## Slug
`enable-ux-auditor-flow-replay-inputs-broad-read-alt-b`

## Scope
`backend`

## Goal
Prepare the backend-facing story that broadly covers the direction's end-to-end UX auditor replay input path: invocation payload composition, runtime/browser input availability, and scheduled-run evidence output, while preserving the direction's exact acceptance criteria and explicit testability gaps.

# Acceptance Criteria

1. `UX auditor invocation includes extracted flow.md files in its input payload.`
2. `UX auditor can access a live app URL in a browser-enabled sandbox and execute semantic Playwright locators against it.`
3. `A scheduled run returns evidence from observed steps rather than reporting missing runtime inputs.`

### Testable Claims (EARS)
AC1.1: WHEN the UX auditor invocation payload is assembled for a run, THE invocation payload SHALL include extracted `flow.md` files.
AC2.1: WHEN the UX auditor runs in a browser-enabled sandbox, THE UX auditor SHALL be able to access a live app URL.
AC2.2: WHEN the UX auditor runs in a browser-enabled sandbox against the live app URL, THE UX auditor SHALL execute semantic Playwright locators against it.
AC3.1: WHEN a scheduled UX auditor run completes with the required runtime inputs available, THE scheduled run result SHALL return evidence from observed steps.
AC3.2: WHEN a scheduled UX auditor run completes with the required runtime inputs available, THE scheduled run result SHALL report observed-step evidence rather than missing runtime inputs.

# Tasks / Subtasks

- [ ] Trace current UX auditor invocation path and identify the boundary where input payload is built.
- [ ] Add extracted `flow.md` content to the UX auditor invocation payload contract.
- [ ] Preserve compatibility for directions where `flow.md` is absent.
- [ ] Trace current sandbox/runtime provisioning path for UX auditor runs.
- [ ] Define backend/runtime contract for passing a live app URL into browser-enabled runs.
- [ ] Ensure the browser-enabled run contract exposes the app target needed by replay execution.
- [ ] Trace scheduled UX audit execution and report formatting path.
- [ ] Update scheduled-run result shaping to surface observed-step evidence when replay executes.
- [ ] Remove or bypass the missing-runtime-input failure path when required replay inputs are present.
- [ ] Add or update backend tests for payload composition.
- [ ] Add or update integration/scheduler tests for observed-step evidence reporting.
- [ ] Document any unresolved gaps where runtime provisioning lives outside backend ownership.

# Dev Notes

## Flow / API embeds

[flow.md: none provided in direction]

[api_spec.md: none provided in direction]

## Context pointers to load

- [Source: context/project.md#Identity]
- [Source: context/project.md#Stack]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/current-state.md#UX auditor] 
- [Source: context/current-state.md#Scheduling] 
- [Source: context/current-state.md#Runtime provisioning] 
- [Source: context/modules/backend.md#Background jobs and service boundaries]
- [Source: context/modules/backend.md#Testing]
- [Source: context/modules/security.md#Runtime and token handling]

## Direction acceptance criteria verbatim

- [ ] UX auditor invocation includes extracted flow.md files in its input payload.
- [ ] UX auditor can access a live app URL in a browser-enabled sandbox and execute semantic Playwright locators against it.
- [ ] A scheduled run returns evidence from observed steps rather than reporting missing runtime inputs.

## Scope notes

- Broad-read interpretation: keep this story end-to-end across the backend-owned seams that connect invocation payload creation, runtime input handoff, and scheduled output formatting.
- Do not invent a `flow.md` artifact; direction explicitly says `(none)`.
- Do not invent an `api_spec.md` contract; direction explicitly says `(none)`.
- PM decomposition shows likely vertical slices; this broad-read story may touch the same seams for a single cohesive backend-ready spec without collapsing implementation tasks into code.
- If `context/current-state.md` lacks explicit sections for UX auditor, scheduling, or runtime provisioning, reviewer/test-designer should treat those as discovery gaps and anchor on actual code paths instead.

## Explicit ambiguity callouts for Dev + Reviewer

- `extracted flow.md files` is direction wording, but the direction also provides no `flow.md`; implementation must define behavior for absent flow artifacts without weakening AC1.
- `live app URL` does not specify environment source, lifecycle, or ownership; backend changes must not assume infra behavior that is not already present.
- `observed steps` / `evidence` do not specify schema; tests should verify the observable report content at the existing scheduler output boundary.

# References

- `direction.md`
- `context/project.md`
- `context/navigation.md`
- `context/current-state.md`
- `context/modules/backend.md`
- `context/modules/security.md`
- `factory/artifacts/story_template.md`

# Dev Agent Record

## Status
Not started

## Notes
- Reserved for implementation agent.
- Record exact files changed.
- Record any discovered ownership split between backend and infra.

# Senior Developer Review

## Status
Pending

## Review checklist
- [ ] Verbatim acceptance criteria preserved.
- [ ] Testable Claims map cleanly to AC1-AC3.
- [ ] No invented API contract or flow narrative.
- [ ] Backend/integration boundaries called out where infra ownership may apply.
- [ ] Scheduler output expectations remain observable and testable.

# Review Follow-ups

- [ ] None yet.
