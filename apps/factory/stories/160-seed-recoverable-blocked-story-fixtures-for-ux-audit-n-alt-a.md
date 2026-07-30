# Story

## Title
Seed recoverable blocked-story fixtures for UX audit — narrow read

## Slug
`seed-recoverable-blocked-story-fixtures-for-ux-audit-n-alt-a`

## Scope
`test`

## Summary
Create only the deterministic seeded fixture path for a blocked story plus merged-PR state, limited to loading/proving the fixture is executable. Do not implement the one-tick transition runner or the audit runbook in this story.

# Acceptance Criteria

- [ ] UX audit can load a seeded blocked story, advance one tick, and capture before/after status evidence for the revival step.

### Testable Claims (EARS)
AC1.1: WHEN the UX audit loads the seeded blocked story fixture, THE system SHALL provide a seeded blocked story for the revival step scenario.
AC1.2: WHEN the UX audit advances one tick from the seeded blocked story fixture, THE system SHALL support the revival step scenario's next-tick execution.
AC1.3: WHEN the UX audit observes the revival step scenario before and after the tick, THE system SHALL make before/after status evidence capturable.

# Tasks / Subtasks

- [ ] Identify existing test/runtime fixture entrypoints for story state seeding.
- [ ] Add deterministic fixture data for a blocked story scenario.
- [ ] Add deterministic fixture data for already-merged PR state paired to that blocked story.
- [ ] Ensure fixture naming/path is audit-discoverable and stable.
- [ ] Add a smoke/integration test that loads the seeded fixture successfully.
- [ ] Assert the loaded initial state is blocked and linked to merged-PR recovery context.
- [ ] Confirm fixture output is suitable for later one-tick execution without adding tick logic here.
- [ ] Record exact fixture identifiers/entrypoints in Dev Notes or inline comments where appropriate.

# Dev Notes

## Scope boundary
- This is the narrow-read fixture-seeding story only.
- In scope: deterministic seeded blocked-story + merged-PR setup; load proof.
- Out of scope: implementing the one-tick revival execution path; capturing final before/after evidence artifact formatting; operator runbook/docs.

## flow.md
# User flow

1. Flow: 013-revive-a-story-whose-pr-was-merged-after-ci-block/flow.md
2. Step: 5
3. Evidence: Step depends on observing asynchronous story state transitions on 'the next tick' after a PR merge, but the provided runtime contains no deploy URL, no browser sandbox, and no executable integration environment for queue/tick/PR state changes.
4. Suggestion: Add an integration-ready audit mode with seeded story/PR fixtures so revival transitions can be observed empirically.

## api_spec.md
(none)

## Acceptance Criteria (verbatim from direction)
- [ ] UX audit can load a seeded blocked story, advance one tick, and capture before/after status evidence for the revival step.

## Context pointers
- No canonical context files were provided in the prelude.
- No `context/project.md` available.
- No `context/navigation.md` available.
- No module/current-state pointers available.
- Dev must derive fixture insertion points from repository code under test on implementation.
- Test-Designer should flag absence of canonical context and inspect repository fixture/runtime surfaces directly.

## Implementation notes
- The fixture must encode two facts together: story is currently blocked; associated PR is already merged.
- The fixture must be deterministic and re-runnable.
- The fixture must be loadable by an executable test/integration path, not static docs-only data.
- The fixture should expose stable identifiers so the backend follow-up story can target it for one-tick execution.
- If the runtime has no dedicated fixture loader, implement the smallest deterministic test harness needed to materialize the seeded state, but keep this story limited to setup/load proof.
- Because `api_spec.md` is `(none)`, there is no API contract to embed or constrain fixture shape.
- Because the direction carries only one broad AC, downstream review should verify this story remains a strict subset enabling that AC rather than claiming full completion alone.

# References

- Direction: `D016 seed recoverable blocked-story fixtures for UX audit`
- PM child-story context: `D016 add blocked-story + merged-PR audit seed fixture`
- Related follow-up story expected in sequence: one-tick revival evidence integration path
- Related follow-up story expected in sequence: UX audit fixture runbook

# Dev Agent Record

## Agent Model Used
- TBD

## Debug Log References
- TBD

## Completion Notes
- TBD

## File List
- TBD

# Senior Developer Review

- TBD

# Review Follow-ups

- TBD
