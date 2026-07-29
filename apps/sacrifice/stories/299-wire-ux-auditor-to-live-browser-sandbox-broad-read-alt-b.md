# Story

## Title
Wire UX auditor to live browser sandbox — broad read

## Slug
`wire-ux-auditor-to-live-browser-sandbox-broad-read-alt-b`

## Scope
`infra`

## Summary
Enable the runtime/sandbox path required for `ux_auditor` executions to launch and use a live browser session, with validation hooks that make the browser-backed execution path observable to downstream evidence-emission work.

# Acceptance Criteria

- [ ] ux_auditor runs with browser access and can emit findings citing Playwright locator actions, response timings, or axe rule ids.

### Testable Claims (EARS)
AC1.1: WHEN `ux_auditor` is executed through the supported sandbox runtime, THE sandbox/runtime SHALL provide browser access to that execution.
AC1.2: WHEN `ux_auditor` runs with browser access, THE `ux_auditor` execution path SHALL be capable of emitting findings citing Playwright locator actions, response timings, or axe rule ids.

# Tasks / Subtasks

- [ ] Identify current `ux_auditor` execution entrypoint and sandbox boundary.
- [ ] Add browser-capable runtime wiring for the supported sandbox path.
- [ ] Ensure required browser dependencies/assets are available in that runtime.
- [ ] Add deterministic configuration/env switches for enabling browser-backed runs.
- [ ] Keep non-browser execution paths unchanged unless explicitly routed.
- [ ] Add a runtime smoke path proving browser launch/use is possible from `ux_auditor` context.
- [ ] Add automated coverage for sandbox/browser availability handshake.
- [ ] Add automated coverage that the wired path exposes the prerequisites needed for evidence-citing findings.
- [ ] Capture failure behavior for missing browser capability/dependencies.
- [ ] Verify story does not implement final evidence formatting beyond runtime enablement needed by downstream story.

# Dev Notes

## Scope notes
- This is the broad-read infra story for direction D100.
- Focus: runtime wiring, sandbox capability, dependency/bootstrap, and observability of browser-backed execution readiness.
- Do not treat this story as the place to redesign UX-auditor finding schemas or final evidence rendering; downstream story owns output semantics built on this runtime.
- The PM decomposition context indicates this story is the dependency slice for later evidence-emission and operator-documentation stories.

## flow.md
[flow.md: none]

## api_spec.md
[api_spec.md: none]

## Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Stack]
- [Source: context/project.md#Top-level layout]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#Task scope: infra]

## Direction acceptance criteria (verbatim)
- [ ] ux_auditor runs with browser access and can emit findings citing Playwright locator actions, response timings, or axe rule ids.

## Implementation guidance for Dev/Test handoff
- Treat runtime browser capability as the primary deliverable.
- Make the supported invocation path explicit in code/config so downstream personas can target one stable execution route.
- Validation should prove that a `ux_auditor` run can reach a live browser context in the sandbox, not merely that Playwright packages are installed.
- Failure messages for missing browser capability should be actionable and distinguish setup/runtime issues from auditor logic issues.
- Preserve existing app constraints from `context/project.md`: avoid unnecessary service bring-up and keep changes minimal to the tooling/runtime layer implicated by this direction.

# References

- Direction: `direction.md`
- PM decomposition context: `pm_result.child_stories`
- Canonical context: `context/project.md`
- Canonical context: `context/navigation.md`

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
