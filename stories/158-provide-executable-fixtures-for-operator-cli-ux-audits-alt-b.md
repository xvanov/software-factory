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
- [x] UX audit runtime can execute documented `factory` CLI flows or consume recorded fixtures with command output and state evidence for each step.

### Testable Claims (EARS)
AC1.1: WHEN the UX audit runtime evaluates a documented `factory` CLI flow and live execution is unavailable, THE runtime SHALL consume recorded fixtures.
AC1.2: WHEN the UX audit runtime evaluates a documented `factory` CLI flow using recorded fixtures, THE fixtures SHALL include command output for each step.
AC1.3: WHEN the UX audit runtime evaluates a documented `factory` CLI flow using recorded fixtures, THE fixtures SHALL include state evidence for each step.
AC1.4: WHEN the UX audit runtime has execution capability for documented `factory` CLI flows, THE runtime SHALL execute the documented `factory` CLI flows.

# Tasks / Subtasks
- [x] Confirm broad-read scope spans contract, capture, and audit-consumption path for recorded CLI fixtures.
- [x] Identify existing UX audit entrypoint and current failure point for text-only runtime.
- [x] Define fixture artifact contract for documented CLI steps.
  - [x] Represent step identity and ordering.
  - [x] Represent invoked command.
  - [x] Represent captured command output.
  - [x] Represent state evidence linked to the same step.
  - [x] Represent provenance needed for audit review.
- [x] Implement fixture loader/parser for the chosen contract.
- [x] Add validation for missing or malformed step evidence.
- [x] Capture at least one audited fixture for the blocked operator step from D012 flow step 1.
  - [x] Include `factory tick --app factory` command evidence.
  - [x] Include resulting state inspection evidence.
- [x] Wire UX audit runtime to consume recorded fixtures when live execution is unavailable.
- [x] Preserve path for live execution if runtime capability exists.
- [x] Add automated tests for fixture loading and audit consumption.
  - [x] Happy path: complete fixture with command output and state evidence.
  - [x] Failure path: missing command output for a documented step.
  - [x] Failure path: missing state evidence for a documented step.
  - [x] Fallback path: recorded fixture used when runtime is text-only.
- [x] Document fixture locations and invocation expectations in story-local implementation notes/comments as needed.

# Dev Notes

## Flow Embed (verbatim)
# User flow

1. Flow: 012-persist-direction-status-in-the-database/flow.md
2. Step: 1
3. Evidence: Flow requires CLI commands (`factory tick --app factory`) and database/state inspection, but runtime context shows `Scheduler transport: text_run` and `Deploy: disabled`; no live app/browser sandbox was available to execute or observe the documented operator step.
4. Suggestion: Run this audit only when the sandbox can execute the factory CLI against a provisioned app state, or provide captured command outputs as audit fixtures.

## API Spec Embed (verbatim)
(none)

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
- Defined fixture contract as dataclasses in `factory/testing/ux_fixtures.py` (CliAuditFixture, FixtureStep, CommandOutput, StateEvidence, StepProvenance, FixtureValidationError)
- Implemented YAML loader (`load_fixture`, `load_fixtures_for_flow`) and validator (`validate_fixture`, `validate_fixture_or_raise`)
- Created recorded fixture for D012 step 1 at `tests/fixtures/ux_audit/012-persist-direction-status-in-the-database.yaml` with command output, state evidence, and provenance
- Wired `_ux_auditor_fixture_run` into `_live_run` in `scheduled_tasks.py`: when `Deploy: disabled` for UX auditor, consumes recorded fixtures; preserves live LLM path when deploy is enabled
- Added 24 automated tests covering happy path, missing command output, missing state evidence, fixture loading, validation, and integration

## Files Touched
- `factory/testing/ux_fixtures.py` (new) — fixture contract, loader, validator
- `factory/chain/scheduled_tasks.py` — added `_ux_auditor_fixture_run` and wired into `_live_run`
- `tests/fixtures/ux_audit/012-persist-direction-status-in-the-database.yaml` (new) — recorded fixture
- `tests/test_ux_fixtures.py` (new) — 24 test cases

## Test Evidence
- `uv run pytest tests/test_ux_fixtures.py tests/test_ux_auditor.py tests/test_scheduled_persona.py -q` passed.
- `uv run pytest -q` passed (full suite green).

## Notes
- Fixture files in `tests/fixtures/ux_audit/` are keyed by flow source in the YAML `flow_source` field
- `load_fixtures_for_flow` matches fixtures by the flow label that `_collect_flow_artifacts` produces (e.g. `012-persist-direction-status-in-the-database/flow.md`)
- The D012 fixture has three state evidence items: two DB queries and one file_exists check

# Senior Developer Review
- Pending

# Review Follow-ups
- Pending