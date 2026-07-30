# Story

## Title
Seed recoverable blocked-story fixtures for UX audit — broad read

## Slug
`seed-recoverable-blocked-story-fixtures-for-ux-audit-b-alt-b`

## Scope
`test`

## Intent
Provide the audit-ready executable fixture path for a recoverable blocked-story scenario, scoped broadly enough to include the deterministic seed, the minimal one-tick execution hook needed to exercise it in test/runtime context, and the evidence capture path required by the UX audit.

# Acceptance Criteria

- [ ] UX audit can load a seeded blocked story, advance one tick, and capture before/after status evidence for the revival step.

### Testable Claims (EARS)
AC1.1: WHEN the UX audit loads the seeded blocked-story fixture, THE system SHALL provide a seeded blocked story for the revival scenario
AC1.2: WHEN the UX audit advances runtime by one tick against the seeded blocked-story fixture, THE system SHALL execute the revival step transition
AC1.3: WHEN the UX audit observes the seeded blocked-story fixture before and after the one-tick advance, THE system SHALL make before/after status evidence capturable for the revival step

# Tasks / Subtasks

- [ ] Identify the existing test/runtime entrypoint that can load deterministic fixture state
- [ ] Add deterministic fixture data for a blocked story paired with already-merged PR state
- [ ] Ensure fixture naming/path is stable and audit-invocable
- [ ] Add or expose minimal one-tick execution path usable from integration/test context
- [ ] Capture pre-tick observable story status from the seeded fixture path
- [ ] Capture post-tick observable story status after exactly one tick
- [ ] Add an automated integration/smoke test covering load -> tick -> before/after evidence capture
- [ ] Verify the fixture path is executable without browser/deploy dependencies
- [ ] Record invocation details and evidence surface expected by downstream docs story

# Dev Notes

## Direction acceptance criteria (verbatim)

- [ ] UX audit can load a seeded blocked story, advance one tick, and capture before/after status evidence for the revival step.

## flow.md (verbatim)

# User flow

1. Flow: 013-revive-a-story-whose-pr-was-merged-after-ci-block/flow.md
2. Step: 5
3. Evidence: Step depends on observing asynchronous story state transitions on 'the next tick' after a PR merge, but the provided runtime contains no deploy URL, no browser sandbox, and no executable integration environment for queue/tick/PR state changes.
4. Suggestion: Add an integration-ready audit mode with seeded story/PR fixtures so revival transitions can be observed empirically.

## api_spec.md (verbatim)

(none)

## Context pointers

No canonical context files were provided in the prelude.

- [Source: context/current-state.md#N/A] Not available in this invocation.
- [Source: context/project.md#N/A] Not available in this invocation.
- [Source: context/navigation.md#N/A] Not available in this invocation.

## Implementation constraints

- No repo context is available; derive exact fixture and entrypoint locations from code inspection.
- Keep scope aligned to executable audit evidence, not full audit environment construction.
- If no controllable tick entrypoint exists, implement the smallest deterministic integration/test harness that advances exactly one tick.
- Evidence must be observable at integration/runtime level; browser UI is not required.
- Preserve deterministic fixture state so downstream docs/test work can reference a stable invocation path.

## Story-prep notes for downstream personas

- This broad-read story intentionally spans the minimum end-to-end executable path because the single direction AC couples fixture loading, one-tick advancement, and before/after evidence capture into one testable outcome.
- If implementation reveals a naturally separable fixture-only layer, keep internal commits granular, but the story is accepted only when the full load -> tick -> evidence path is executable.

# References

- Direction: `D016 seed recoverable blocked-story fixtures for UX audit`
- PM tracker title: `D016 seed recoverable blocked-story fixtures for UX audit`
- Assigned story slug: `seed-recoverable-blocked-story-fixtures-for-ux-audit-b-alt-b`
- Related PM child stories for decomposition context:
  - `D016 add blocked-story + merged-PR audit seed fixture`
  - `D016 add one-tick revival evidence integration path`
  - `D016 document UX audit fixture runbook for revival step`

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
