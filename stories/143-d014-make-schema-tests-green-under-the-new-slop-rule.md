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

# Dev Agent Record

## Status
Done

## Completion Notes
- Audited schema-related repository tests for unsuppressed `direct_db_bootstrap` findings using `scan_file`.
- Refactored `tests/test_directions_schema.py` setup sites that directly called `create_engine`/`SQLModel.metadata.create_all` inside test bodies so they now drive `factory.observability.schema.migrate` (directly or via `_seeded_engine`).
- Added a single-test `# noqa: slop` suppression to `tests/test_usage_honesty.py::test_both_stories_migration_paths_apply_the_same_columns` because that test intentionally exercises a raw-engine migration parity path.
- Added regression coverage in `tests/test_slop_detector.py` asserting schema-related repo tests have no unsuppressed `direct_db_bootstrap` findings.
- Verified detector-focused, gate-focused, and full-suite runs are green.

## File List
- `tests/test_directions_schema.py`
- `tests/test_usage_honesty.py`
- `tests/test_slop_detector.py`
- `stories/143-d014-make-schema-tests-green-under-the-new-slop-rule.md`

## Verification
- `uv run pytest -q tests/test_slop_detector.py::test_schema_related_repo_tests_have_no_unsuppressed_direct_bootstrap_findings` (red before implementation, then green after updates)
- `uv run pytest -q tests/test_slop_detector.py tests/test_directions_schema.py tests/test_usage_honesty.py`
- `uv run pytest -q tests/test_gates_evaluation.py -k tests_meaningful`
- `uv run pytest -q`
