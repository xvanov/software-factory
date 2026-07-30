# Story

## Title
D014 make schema tests green under the new slop rule

## Slug
`d014-make-schema-tests-green-under-the-new-slop-rule`

## Scope
`test`

## Summary
Audit and minimally update `factory/observability/schema.py`-related tests so repository-owned tests remain green once the new slop detector flags direct test bootstrap calls. Legitimate raw-engine coverage must either avoid the finding or use the existing `# noqa: slop` single-test suppression.

# Acceptance Criteria

- `factory/observability/schema.py`'s own tests, which legitimately construct engines, either pass or carry the escape hatch — the repository's own suite must be green with the new pattern enabled.
- The existing `# noqa: slop` escape hatch suppresses the new finding on a single test, for the case where exercising the raw engine IS the subject — for example a test of `migrate()` itself.
- The detector reports a finding with a stable new `kind` when a test file calls `SQLModel.metadata.create_all` or a `create_engine` variant directly.
- The finding carries a `why_slop` explanation naming the app initializer the test should have called, so the message teaches rather than just blocks.

### Testable Claims (EARS)
AC1.1: WHEN the repository test suite is run with the new slop pattern enabled, GIVEN a test under `factory/observability/schema.py` coverage legitimately constructs engines, THE test SHALL either produce no finding or be suppressed with the existing escape hatch so the suite remains green.
AC2.1: WHEN a single test that exercises the raw engine or `migrate()` itself includes `# noqa: slop`, THE detector SHALL suppress the new finding for that single test.
AC3.1: WHEN a test file calls `SQLModel.metadata.create_all` directly, THE detector SHALL report a finding with a stable new `kind`.
AC3.2: WHEN a test file calls a `create_engine` variant directly, THE detector SHALL report a finding with a stable new `kind`.
AC4.1: WHEN the detector reports the new finding, THE finding SHALL carry a `why_slop` explanation naming the app initializer the test should have called.

# Tasks / Subtasks

- [ ] Identify repository-owned tests covering `factory/observability/schema.py`
- [ ] Audit those tests for direct `SQLModel.metadata.create_all` usage
- [ ] Audit those tests for direct `sqlmodel.create_engine` usage
- [ ] Audit those tests for direct `sqlalchemy.create_engine` usage
- [ ] Classify each flagged occurrence as legitimate raw-engine subject vs accidental bypass
- [ ] For legitimate raw-engine subject tests, add `# noqa: slop` at single-test scope only
- [ ] For accidental bypass tests, rewrite setup to drive `factory.observability.schema.migrate` or the app-owned initializer path
- [ ] Keep coverage intent unchanged for schema behavior under test
- [ ] Add/update tests proving repository-owned schema tests are clean or intentionally suppressed
- [ ] Run detector-focused tests covering the new kind against schema-related tests
- [ ] Run `tests-meaningful` path and confirm no repo-owned unsuppressed findings remain from schema tests
- [ ] Record exact files updated and rationale in Dev Agent Record

# Dev Notes

## Scope notes
- This story is limited to repo-suite cleanup and explicit suppression where justified.
- Do not broaden detector behavior here.
- Do not add a new suppression mechanism.
- Prefer the smallest change that preserves the subject of each schema test.

## Embedded flow.md
[flow.md: see d014-add-slop-kind-for-direct-test-db-bootstrap-calls Dev Notes for verbatim embed]

## Embedded api_spec.md
(none)

## Context pointers
- No canonical context files were provided in the prelude.
- Load and inspect the implementation and tests directly in repo paths relevant to this story:
  - `factory/observability/schema.py`
  - schema-related test files covering `migrate()` and engine/bootstrap behavior
  - detector and gate files changed by preceding D014 stories

## Verbatim direction acceptance criteria
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

## Implementation constraints for this story
- Treat the detector's stable new `kind` as pre-existing input from earlier D014 work; consume it, do not redefine it.
- Respect existing `# noqa: slop` semantics exactly; suppression must remain single-test scoped.
- Repository-owned schema tests may legitimately exercise raw engine/bootstrap behavior only when that behavior is itself the subject.
- If a schema test's real subject is app initialization behavior, route it through `factory.observability.schema.migrate` rather than direct bootstrap calls.
- Keep the repository suite green without turning this story into a broad migration of unrelated tests.
- If `factory/observability/schema.py` tests need suppression, make the suppression explicit and local so reviewers can see why the exception exists.

# References

- Direction: `D014 detect tests that bypass the app entry point`
- Primary initializer named by direction: `factory.observability.schema.migrate`
- In-scope production module: `factory/observability/schema.py`
- Related earlier D014 stories:
  - detector kind implementation
  - suppression/app-initializer clean-path proof
  - story-148 regression fixture coverage
  - tests-meaningful gate verification

# Dev Agent Record

## Status
Not started

## Files to Inspect
- `factory/observability/schema.py`
- schema-related test files
- detector rule file defining the new slop kind
- existing suppression handling for `# noqa: slop`
- `tests-meaningful` gate path files

## Expected File Changes
- Minimal modifications to schema-related tests
- No new gate label
- No new suppression mechanism

## Notes for Dev
- Preserve test intent first.
- Suppress only where raw-engine behavior is the actual subject.
- Rewrite setup instead of suppressing when the test is supposed to exercise the app entry point.

# Senior Developer Review

- [ ] Schema-related tests audited for all direct bootstrap calls in test code
- [ ] Each suppression justified by test subject, not convenience
- [ ] Any rewritten test now drives app-owned initialization path
- [ ] No broadened detector behavior introduced in this story
- [ ] Repo suite remains green with new rule enabled
- [ ] Suppressions remain local and single-test scoped

# Review Follow-ups

- [ ] Verify no additional repo-owned tests outside schema coverage need the same treatment
- [ ] Confirm reviewer can distinguish legitimate raw-engine tests from accidental bypass tests from diffs alone
