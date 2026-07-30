# Story

## Title
D014 prove noqa suppression and app-initializer clean path

## Slug
`d014-prove-noqa-suppression-and-app-initializer-clean-path`

## Scope
`test`

## Summary
Add focused regression tests for the new direct-test-DB-bootstrap slop kind to prove two user-visible edges: `# noqa: slop` suppresses a single-test finding, and a test that drives `factory.observability.schema.migrate` instead of raw engine/bootstrap calls produces no finding.

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
AC1.1: WHEN the detector analyzes a Python test file that directly calls `SQLModel.metadata.create_all`, THE detector SHALL report a finding with a stable new `kind`
AC1.2: WHEN the detector analyzes a Python test file that directly calls a `create_engine` variant, THE detector SHALL report a finding with a stable new `kind`
AC2.1: WHEN the detector reports the new direct-bootstrap finding, THE finding SHALL carry a `why_slop` explanation naming the app initializer the test should have called
AC3.1: WHEN the detector analyzes a Python test file that obtains its database through the application's initializer, THE detector SHALL produce no finding for the new direct-bootstrap pattern
AC3.2: WHEN the detector analyzes the fixed form of the story-148 test, THE detector SHALL produce no finding for the new direct-bootstrap pattern
AC4.1: WHEN a single test using the new direct-bootstrap pattern is marked with `# noqa: slop`, THE detector SHALL suppress the new finding for that single test
AC5.1: UNTESTABLE-AS-WRITTEN — missing the specific repository test files and exact expected disposition for each file under this story's scope
AC6.1: UNTESTABLE-AS-WRITTEN — gate-blocking behavior requires diff/gate-path setup beyond this story's scoped test proof unless explicitly identified in tasks/fixtures
AC7.1: WHEN the detector analyzes the exact story-148 bad test body, THE detector SHALL flag it
AC7.2: WHEN the detector analyzes the fixed form of the story-148 test, THE detector SHALL not flag it

# Tasks / Subtasks

- [x] Identify detector test module covering Python slop-pattern findings
- [x] Add fixture/case: direct bootstrap call plus `# noqa: slop` on a single test
- [x] Assert suppressed case emits no new direct-bootstrap finding
- [x] Add fixture/case: test body that drives `factory.observability.schema.migrate`
- [x] Assert app-initializer case emits no new direct-bootstrap finding
- [x] Keep assertions scoped to this story's edges only: suppression and clean path
- [x] Reuse stable new `kind` constant/name from detector story; do not redefine semantics here
- [x] Verify tests remain isolated from gate-plumbing assertions owned by sibling stories
- [x] Run targeted test file(s)
- [x] Record exact commands and outcomes in Dev Agent Record

# Dev Notes

## Scope notes
- This story depends on the detector shape introduced by `D014 add slop kind for direct test DB bootstrap calls`.
- This story proves only two user-visible edges: single-test suppression via `# noqa: slop`, and the no-finding path when the test drives `factory.observability.schema.migrate`.
- Do not absorb gate-path proof, exact story-148 body regression fixture, or repo-suite cleanup beyond what is necessary for these focused tests.

## flow.md
# Operator flow — catching a test that cannot fail

1. **A story ships a test that bypasses the app.** A dev writes a test that calls
   `SQLModel.metadata.create_all` directly and asserts a table exists.

2. **The gate blocks the PR.** The operator sees `tests-meaningful` red on that
   PR, with a slop finding naming the file, the line, and the offending call —
   not a generic "test quality" complaint.

3. **The message says what to do.** The finding's explanation names the
   application initializer the test should have driven
   (`factory.observability.schema.migrate`), so the fix is obvious without
   reading the detector's source.

4. **The dev fixes it and the gate clears.** The rewritten test drives the app's
   initializer, produces no finding, and the PR goes green — and now genuinely
   fails when production is broken.

5. **A legitimate raw-engine test is not blocked.** The operator marks a test
   whose actual subject IS the engine or `migrate()` itself with `# noqa: slop`,
   and the gate accepts it.

6. **The existing suite stays green.** The operator runs the full suite with the
   new pattern enabled and sees no new failures, so enabling the rule does not
   itself become a migration project.

## api_spec.md
(none)

## Context pointers
- No canonical context files were provided in this invocation.
- Load implementation/test context directly from repository files that define:
  - the Python slop detector rule set
  - existing `# noqa: slop` suppression behavior
  - current detector fixture/test harness for Python test-file scanning
  - `factory.observability.schema.migrate`

## Direction acceptance criteria (verbatim)
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

## Notes for Dev/Test Designer
- The suppression proof must demonstrate single-test granularity, not blanket file suppression, unless the existing harness only supports one-test-per-file fixtures.
- The clean-path proof must exercise the application-owned initializer by name: `factory.observability.schema.migrate`.
- If the detector fixture language requires synthetic test file bodies, keep them minimal and line-stable so line-number assertions remain robust.
- If the exact story-148 body fixture is introduced in the sibling regression story, do not duplicate it here; use a narrower clean-path example unless shared fixtures already exist.

# References

- Direction: `D014 detect tests that bypass the app entry point`
- Tracker title: `D014 detect tests that bypass the app entry point`
- Related story dependency: `D014 add slop kind for direct test DB bootstrap calls`
- Related follow-on stories:
  - `D014 add story-148 regression fixture and exact-body coverage`
  - `D014 verify tests-meaningful gate blocks new bypass findings`
  - `D014 make schema tests green under the new slop rule`

# Dev Agent Record

## Implementation Log
- [x] Added `test_noqa_slop_is_single_test_granularity` in `tests/test_slop_detector.py` to prove `# noqa: slop` suppresses only the annotated test function while an unsuppressed neighboring test in the same file is still flagged.
- [x] Verified existing story-scoped regression coverage remains intact for:
  - stable `kind` = `direct_db_bootstrap` on direct `create_all`/`create_engine` usage (AC1.1, AC1.2)
  - `why_slop` guidance naming `factory.observability.schema.migrate` (AC2.1)
  - no-finding path when tests call `migrate` (AC3.1, AC3.2, AC7.2)
  - exact story-148 bad body flagged (AC7.1)
- [x] AC5.1 and AC6.1 remain UNTESTABLE-AS-WRITTEN in this story scope.

## Commands Run
- `python -m pytest tests/test_slop_detector.py::test_noqa_slop_is_single_test_granularity -q` - passed
- `python -m pytest tests/test_slop_detector.py tests/test_gates_evaluation.py tests/test_observability_schema.py -q` - passed
- `python -m pytest tests/test_acceptance_oracle.py::test_gate_passes_when_code_satisfies_acs tests/test_acceptance_oracle.py::test_gate_fails_on_ac_violation_even_when_dev_tests_green tests/test_acceptance_oracle.py::test_gate_blocks_then_passes_after_reauthor tests/test_ears_property_oracle.py::test_property_oracle_passes_on_correct_code tests/test_ears_property_oracle.py::test_property_oracle_fails_on_violation_even_when_dev_tests_green tests/test_gates_evaluation.py::test_tests_meaningful_ablation_fails_on_unexercised_symbol -q` - 5 passed, 1 failed (`test_property_oracle_fails_on_violation_even_when_dev_tests_green`, unrelated to this story)
- `python -m pytest -q` - failed with pre-existing unrelated issues in optional dependency/runtime-oracle areas (`litellm`/`textual` import tests and estimated-cost audit assertions)

## Files Touched
- `tests/test_slop_detector.py` - added single-test-granularity suppression regression test
- `stories/140-d014-prove-noqa-suppression-and-app-initializer-clean-path.md` - refreshed Dev Agent Record for this run

## Result
- Story edges are proven by executable tests: direct-bootstrap detection remains active, `# noqa: slop` works at single-test granularity, and `factory.observability.schema.migrate` path remains clean.
- Targeted D014-related suite is green after changes.
- Broader suite currently contains unrelated failures outside this story's scope (acceptance/property oracle expectation text and optional dependencies).

# Senior Developer Review

- [ ] Pending

# Review Follow-ups

- [ ] Pending