# Story

## Title
D014 verify tests-meaningful gate blocks new bypass findings

## Story
**As a** maintainer of the slop detector
**I want** to prove the new `direct_db_bootstrap` finding reaches the existing `tests-meaningful` gate path and blocks diffs that introduce it
**so that** the gate enforcement path is verified end-to-end, with no new gate label or special-case routing.

## Scope
- Prove gate integration for `direct_db_bootstrap` findings.
- Assert operator-visible output (kind, why_slop, file/line) at gate level.
- Verify no new gate label or routing branch is introduced.

## Acceptance Criteria
- The `tests-meaningful` gate blocks a PR whose diff introduces the new finding, through the existing path, with no new gate label.
- A regression test asserts the exact story-148 test body is flagged, and that its fixed form is not.

(Only gate-scoped ACs are actionable here. Detector mechanics, suppression, exact-body regression, and schema-test cleanup belong to sibling stories.)

### Testable Claims (EARS)
AC6.1: WHEN a PR diff introduces the new finding, THE `tests-meaningful` gate SHALL block the PR through the existing path
AC6.2: WHEN the `tests-meaningful` gate blocks a PR for the new finding, THE gate SHALL use no new gate label

## Tasks / Subtasks

- [x] Confirm gate integration point for slop findings
  - [x] Identify the existing `tests-meaningful` path that consumes detector findings
  - [x] Locate current gate-label/reporting behavior to preserve unchanged routing
  - [x] Verify where diff-introduced findings are converted into gate failure
- [x] Add focused gate-path coverage for the new finding kind
  - [x] Reuse existing gate harness/fixture style
  - [x] Introduce a diff/test input that contains a direct bootstrap call in a Python test file
  - [x] Assert the resulting gate outcome is blocking/failing via `tests-meaningful`
  - [x] Assert the gate path is the existing one, not a special case
  - [x] Assert no new gate label is introduced
- [x] Prove operator-visible output is tied to the new finding
  - [x] Assert surfaced finding includes the stable new `kind`
  - [x] Assert surfaced finding includes `why_slop` naming `factory.observability.schema.migrate`
  - [x] Assert surfaced output identifies file/line/call through the normal path if existing harness exposes it
- [x] Keep this story scoped to gate plumbing proof
  - [x] Depend on detector-kind mechanics from the earlier infra story
  - [x] Do not re-implement detector behavior here beyond fixtures needed for gate proof
  - [x] Do not add a new gate name, label, or routing branch
- [x] Verify repo safety
  - [x] Run targeted tests covering the `tests-meaningful` gate path
  - [x] Confirm no unrelated gate expectations require updates

## Dev Notes

### Scope notes
This story is gate-plumbing proof only. Detector mechanics, suppression behavior, exact-body regression coverage, and schema-test cleanup belong to sibling stories declared in `pm_result.child_stories`.

### Direction acceptance criteria (verbatim embed)
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

### Suggested evidence to capture in implementation
- The introduced diff contains one offending direct bootstrap call in a Python test file.
- The gate result is failing/blocking under `tests-meaningful`.
- The surfaced finding retains the new `kind` and expected `why_slop` payload.
- No new gate label/name appears anywhere in the result.

## References
- Direction: `D014 detect tests that bypass the app entry point`
- Motivating initializer named by direction: `factory.observability.schema.migrate`
- PM decomposition sibling stories:
  - `D014 add slop kind for direct test DB bootstrap calls`
  - `D014 prove noqa suppression and app-initializer clean path`
  - `D014 add story-148 regression fixture and exact-body coverage`
  - `D014 make schema tests green under the new slop rule`

## Dev Agent Record

### Agent Model Used
- openhands

### Debug Log References
- `uv sync --all-extras`
- `uv run pytest -q tests/test_acceptance_oracle.py::test_gate_fails_on_ac_violation_even_when_dev_tests_green tests/test_ears_property_oracle.py::test_property_oracle_fails_on_violation_even_when_dev_tests_green tests/test_gates_evaluation.py::test_tests_meaningful_ablation_fails_on_unexercised_symbol`
- `uv run pytest -q tests/test_gates_evaluation.py tests/test_slop_detector.py tests/test_observability_schema.py`
- `uv run pytest -q`

### Completion Notes
- Verified the existing `tests-meaningful` gate path is still the enforcement route for slop findings and preserved label/routing behavior.
- Enhanced `test_tests_meaningful_fails_on_direct_db_bootstrap_diff` to assert operator-visible structured finding output: stable `kind`, `why_slop` naming `factory.observability.schema.migrate`, and file/line/code excerpt details.
- Added `test_tests_meaningful_fails_on_SQLModel_metadata_create_all` and `test_tests_meaningful_passes_on_app_initializer_diff` to prove blocking on direct bootstrap and clean pass via app initializer through the same gate path.
- Confirmed full repository safety with green targeted suites and a green full `uv run pytest -q` run.

### File List
- `tests/test_gates_evaluation.py` — enhanced existing gate test and added two focused gate-path tests
- `stories/142-d014-verify-tests-meaningful-gate-blocks-new-bypass-findings.md` — updated Dev Agent Record for this run