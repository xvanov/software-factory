# Story

## Title
D014 verify tests-meaningful gate blocks new bypass findings

## Slug
`d014-verify-tests-meaningful-gate-blocks-new-bypass-findings`

## Scope
`infra`

## Summary
Prove the new direct-test-DB-bootstrap slop finding reaches the existing `tests-meaningful` gate path and blocks diffs that introduce it, with no new gate label or special-case routing.

# Acceptance Criteria

- The detector reports a finding with a stable new `kind` when a test file calls
  `SQLModel.metadata.create_all` or a `create_engine` variant directly.
- The finding carries a `why_slop` explanation naming the app initializer the
  test should have called, so the message teaches rather than just blocks.
- A test that obtains its database through the application's initializer produces
  NO finding, so the fixed form of the story-148 test passes cleanly.
- The existing `# noqa: slop` escape hatch suppresses the new finding on a single
  test, for the case where exercising the raw engine IS the subject — for example
  a test of `migrate()` itself.
- `factory/observability/schema.py`'s own tests, which legitimately construct
  engines, either pass or carry the escape hatch — the repository's own suite must
  be green with the new pattern enabled.
- The `tests-meaningful` gate blocks a PR whose diff introduces the new finding,
  through the existing path, with no new gate label.
- A regression test asserts the exact story-148 test body is flagged, and that its
  fixed form is not.

### Testable Claims (EARS)
AC1.1: WHEN a Python test file calls `SQLModel.metadata.create_all` directly, THE detector SHALL report a finding with a stable new `kind`
AC1.2: WHEN a Python test file calls `sqlmodel.create_engine` directly, THE detector SHALL report a finding with a stable new `kind`
AC1.3: WHEN a Python test file calls `sqlalchemy.create_engine` directly, THE detector SHALL report a finding with a stable new `kind`
AC2.1: WHEN the detector reports the new finding, THE finding SHALL carry a `why_slop` explanation naming `factory.observability.schema.migrate` as the app initializer the test should have called
AC3.1: WHEN a test obtains its database through the application's initializer, THE detector SHALL produce no finding
AC3.2: WHEN the fixed form of the story-148 test drives the application's initializer, THE detector SHALL produce no finding
AC4.1: WHEN a single test carrying the new finding is marked with `# noqa: slop`, THE detector SHALL suppress the new finding for that single test
AC5.1: WHEN the new pattern is enabled and `factory/observability/schema.py` tests legitimately construct engines, THE repository's own suite SHALL remain green by those tests either passing cleanly or carrying the escape hatch
AC6.1: WHEN a PR diff introduces the new finding, THE `tests-meaningful` gate SHALL block the PR through the existing path
AC6.2: WHEN the `tests-meaningful` gate blocks a PR for the new finding, THE gate SHALL use no new gate label
AC7.1: WHEN the exact story-148 test body is scanned, THE detector SHALL flag it
AC7.2: WHEN the fixed form of the story-148 test is scanned, THE detector SHALL not flag it

# Tasks / Subtasks

- [ ] Confirm gate integration point for slop findings
  - [ ] Identify the existing `tests-meaningful` path that consumes detector findings
  - [ ] Locate current gate-label/reporting behavior to preserve unchanged routing
  - [ ] Verify where diff-introduced findings are converted into gate failure
- [ ] Add focused gate-path coverage for the new finding kind
  - [ ] Reuse existing gate harness/fixture style
  - [ ] Introduce a diff/test input that contains a direct bootstrap call in a Python test file
  - [ ] Assert the resulting gate outcome is blocking/failing via `tests-meaningful`
  - [ ] Assert the gate path is the existing one, not a special case
  - [ ] Assert no new gate label is introduced
- [ ] Prove operator-visible output is tied to the new finding
  - [ ] Assert surfaced finding includes the stable new `kind`
  - [ ] Assert surfaced finding includes `why_slop` naming `factory.observability.schema.migrate`
  - [ ] Assert surfaced output identifies file/line/call through the normal path if existing harness exposes it
- [ ] Keep this story scoped to gate plumbing proof
  - [ ] Depend on detector-kind mechanics from the earlier infra story
  - [ ] Do not re-implement detector behavior here beyond fixtures needed for gate proof
  - [ ] Do not add a new gate name, label, or routing branch
- [ ] Verify repo safety
  - [ ] Run targeted tests covering the `tests-meaningful` gate path
  - [ ] Confirm no unrelated gate expectations require updates

# Dev Notes

## Scope notes
This story is gate-plumbing proof only. Detector mechanics, suppression behavior, exact-body regression coverage, and schema-test cleanup belong to sibling stories declared in `pm_result.child_stories`.

## flow.md
[flow.md: see d014-add-slop-kind-for-direct-test-db-bootstrap-calls Dev Notes for verbatim embed]

## api_spec.md
[api_spec.md: see d014-add-slop-kind-for-direct-test-db-bootstrap-calls Dev Notes for verbatim embed]

## Direction acceptance criteria (verbatim embed)
- The detector reports a finding with a stable new `kind` when a test file calls
  `SQLModel.metadata.create_all` or a `create_engine` variant directly.
- The finding carries a `why_slop` explanation naming the app initializer the
  test should have called, so the message teaches rather than just blocks.
- A test that obtains its database through the application's initializer produces
  NO finding, so the fixed form of the story-148 test passes cleanly.
- The existing `# noqa: slop` escape hatch suppresses the new finding on a single
  test, for the case where exercising the raw engine IS the subject — for example
  a test of `migrate()` itself.
- `factory/observability/schema.py`'s own tests, which legitimately construct
  engines, either pass or carry the escape hatch — the repository's own suite must
  be green with the new pattern enabled.
- The `tests-meaningful` gate blocks a PR whose diff introduces the new finding,
  through the existing path, with no new gate label.
- A regression test asserts the exact story-148 test body is flagged, and that its
  fixed form is not.

## Direction pointers
- Gate behavior to prove: existing `tests-meaningful` path blocks a PR when the diff introduces the new finding; no new gate label.
- Narrow detector target: direct calls in Python test files to `SQLModel.metadata.create_all`, `sqlmodel.create_engine`, `sqlalchemy.create_engine`.
- Teaching message requirement: `why_slop` must explicitly name `factory.observability.schema.migrate`.

## Context pointers
No canonical context files were provided in the prelude for this run.

## Implementation constraints
- Reuse the existing gate path; do not add a parallel enforcement path.
- Preserve current gate naming/labeling semantics.
- This story should assert operational outcome at the gate boundary, not broaden rule scope.
- If the gate harness already validates diff-only behavior, use it instead of introducing new plumbing.
- If the harness exposes findings as structured data, prefer asserting structured fields over brittle full-string snapshots.

## Suggested evidence to capture in implementation
- The introduced diff contains one offending direct bootstrap call in a Python test file.
- The gate result is failing/blocking under `tests-meaningful`.
- The surfaced finding retains the new `kind` and expected `why_slop` payload.
- No new gate label/name appears anywhere in the result.

# References

- `direction.md` — source direction for D014
- `flow.md` — operator flow for blocking/fixing/suppressing the finding
- `pm_result.child_stories` — sibling-slice boundaries for detector, suppression, regression, and suite cleanup

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

## Reviewer
- TBD

## Outcome
- TBD

## Review Notes
- TBD

# Review Follow-ups

- [ ] TBD
