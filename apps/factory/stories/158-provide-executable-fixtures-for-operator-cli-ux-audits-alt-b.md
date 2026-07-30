# Story

## Title
Provide executable fixtures for operator CLI UX audits — broad read

## Slug
`provide-executable-fixtures-for-operator-cli-ux-audits-alt-b`

## Scope
`test`

## Summary
Deliver the test-facing story that makes D015 auditable in a text-only environment by defining and validating a recorded-fixture path for documented `factory` CLI UX flows, capturing command output plus state evidence per step, and enabling audit consumption of that evidence as the broad validating slice for the direction.

# Acceptance Criteria

## Verbatim Direction Acceptance Criteria
- [ ] UX audit runtime can execute documented `factory` CLI flows or consume recorded fixtures with command output and state evidence for each step.

### Testable Claims (EARS)
AC1.1: WHEN the UX audit runtime evaluates a documented `factory` CLI flow and live execution is unavailable, THE runtime SHALL consume recorded fixtures.
AC1.2: WHEN the UX audit runtime evaluates a documented `factory` CLI flow using recorded fixtures, THE fixtures SHALL include command output for each step.
AC1.3: WHEN the UX audit runtime evaluates a documented `factory` CLI flow using recorded fixtures, THE fixtures SHALL include state evidence for each step.
AC1.4: WHEN the UX audit runtime has execution capability for documented `factory` CLI flows, THE runtime SHALL execute the documented `factory` CLI flows.

# Tasks / Subtasks
- [ ] Confirm broad-read scope spans contract, capture, and audit-consumption path for recorded CLI fixtures.
- [ ] Identify existing UX audit entrypoint and current failure point for text-only runtime.
- [ ] Define fixture artifact contract for documented CLI steps.
  - [ ] Represent step identity and ordering.
  - [ ] Represent invoked command.
  - [ ] Represent captured command output.
  - [ ] Represent state evidence linked to the same step.
  - [ ] Represent provenance needed for audit review.
- [ ] Implement fixture loader/parser for the chosen contract.
- [ ] Add validation for missing or malformed step evidence.
- [ ] Capture at least one audited fixture for the blocked operator step from D012 flow step 1.
  - [ ] Include `factory tick --app factory` command evidence.
  - [ ] Include resulting state inspection evidence.
- [ ] Wire UX audit runtime to consume recorded fixtures when live execution is unavailable.
- [ ] Preserve path for live execution if runtime capability exists.
- [ ] Add automated tests for fixture loading and audit consumption.
  - [ ] Happy path: complete fixture with command output and state evidence.
  - [ ] Failure path: missing command output for a documented step.
  - [ ] Failure path: missing state evidence for a documented step.
  - [ ] Fallback path: recorded fixture used when runtime is text-only.
- [ ] Document fixture locations and invocation expectations in story-local implementation notes/comments as needed.

# Dev Notes

## Flow Embed (verbatim)
# User flow

1. Flow: 012-persist-direction-status-in-the-database/flow.md
2. Step: 1
3. Evidence: Flow requires CLI commands (`factory tick --app factory`) and database/state inspection, but runtime context shows `Scheduler transport: text_run` and `Deploy: disabled`; no live app/browser sandbox was available to execute or observe the documented operator step.
4. Suggestion: Run this audit only when the sandbox can execute the factory CLI against a provisioned app state, or provide captured command outputs as audit fixtures.

## API Spec Embed (verbatim)
(none)

## Context Pointers
- No canonical context files were provided in the prelude.
- No `context/project.md` available.
- No `context/navigation.md` available.
- No `context/current-state.md` available.
- Dev must derive implementation touchpoints from repository code during execution.
- Test-Designer should flag missing canonical context and anchor tests to the audited flow and direction artifacts in this story.

## Direction Acceptance Criteria Embed (verbatim)
- [ ] UX audit runtime can execute documented `factory` CLI flows or consume recorded fixtures with command output and state evidence for each step.

## Story-Specific Implementation Notes
- Broad-read interpretation intentionally covers the full validating path across the PM decomposition: fixture contract, one recorded operator-flow fixture, and runtime consumption of recorded evidence.
- Primary audited flow is direction 012, step 1, centered on `factory tick --app factory` plus resulting database/state inspection evidence.
- Current runtime limitation is explicit: `Scheduler transport: text_run` and `Deploy: disabled` block empirical live execution in this environment.
- Because `api_spec.md` is `(none)`, no API contract constrains the fixture shape; keep the fixture schema minimal, explicit, and step-addressable.
- Recorded evidence must be sufficient for downstream audit review to verify both operator-visible command behavior and resulting state transition evidence for each documented step in scope.
- If the repo already contains a stable executable audit harness, it may remain supported, but this story is complete only when the recorded-fixture path satisfies the direction acceptance criterion in the blocked environment.
- If no explicit canonical fixture directory exists, choose a repo location consistent with current test assets and make the loader/tests reference that location deterministically.

# References
- Direction: D015 `Provide executable fixtures for operator CLI UX audits`
- Related flow source: `012-persist-direction-status-in-the-database/flow.md` step 1
- PM decomposition context:
  - `D015 define CLI audit fixture contract and sample loader`
  - `D015 record fixture for operator tick CLI flow from D012`
  - `D015 make UX audit runtime consume recorded CLI fixtures`
  - `D015 document how to capture and use CLI audit fixtures`

# Dev Agent Record

## Implementation Log
- Pending

## Files Touched
- Pending

## Test Evidence
- Pending

## Notes
- Pending

# Senior Developer Review
- Pending

# Review Follow-ups
- Pending
