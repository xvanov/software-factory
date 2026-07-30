# Story

## Title
Provide executable fixtures for operator CLI UX audits — narrow read

## Slug
`provide-executable-fixtures-for-operator-cli-ux-audits-alt-a`

## Scope
`test`

## Intent
Land the smallest validating slice for D015 under the narrow read: define and prove a recorded-fixture path for the blocked operator CLI audit instead of enabling live runtime execution.

# Acceptance Criteria

- UX audit runtime can execute documented `factory` CLI flows or consume recorded fixtures with command output and state evidence for each step.

### Testable Claims (EARS)
AC1.1: WHEN the UX audit runtime cannot execute the documented `factory` CLI flows, THE audit runtime SHALL consume recorded fixtures.
AC1.2: WHEN recorded fixtures are consumed for a documented `factory` CLI flow, THE fixture set SHALL include command output for each step.
AC1.3: WHEN recorded fixtures are consumed for a documented `factory` CLI flow, THE fixture set SHALL include state evidence for each step.

# Tasks / Subtasks

- [x] Define fixture contract for recorded CLI audit evidence.
  - [x] Specify required fields for per-step command output.
  - [x] Specify required fields for per-step state evidence.
  - [x] Specify representation for flow identity and step identity.
  - [x] Specify failure behavior for malformed or incomplete fixtures.
- [x] Add sample loader or reader for the fixture contract.
  - [x] Load fixture data from repository path(s) intended for audit inputs.
  - [x] Validate required fields before exposing fixture contents.
  - [x] Return deterministic structure for downstream audit consumers.
- [x] Capture one sample fixture for the blocked operator step referenced by D015.
  - [x] Record `factory tick --app factory` command evidence.
  - [x] Record corresponding state inspection evidence.
  - [x] Tie evidence to flow `012-persist-direction-status-in-the-database/flow.md`, step `1`.
- [x] Add automated tests for contract and loader behavior.
  - [x] Valid fixture loads successfully.
  - [x] Missing command output is rejected.
  - [x] Missing state evidence is rejected.
  - [x] Flow/step mapping is preserved.
- [x] Keep implementation fixture-first.
  - [x] Do not require live CLI execution in this story.
  - [x] Do not broaden scope into audit runtime consumption beyond proving loader readiness.

# Dev Notes

## Scope notes
- Narrow read for D015: satisfy the direction via recorded fixtures only.
- This story is the test-scope enabling slice: contract + loader + one captured example fixture.
- Live runtime execution support is out of scope.
- Full audit-runtime consumption wiring is out of scope for this story.

## flow.md (verbatim embed)
# User flow

1. Flow: 012-persist-direction-status-in-the-database/flow.md
2. Step: 1
3. Evidence: Flow requires CLI commands (`factory tick --app factory`) and database/state inspection, but runtime context shows `Scheduler transport: text_run` and `Deploy: disabled`; no live app/browser sandbox was available to execute or observe the documented operator step.
4. Suggestion: Run this audit only when the sandbox can execute the factory CLI against a provisioned app state, or provide captured command outputs as audit fixtures.

## api_spec.md (verbatim embed)
(none)

## Direction acceptance criteria (verbatim embed)
- [ ] UX audit runtime can execute documented `factory` CLI flows or consume recorded fixtures with command output and state evidence for each step.

## Context pointers
- No canonical context files were provided in this invocation.

## Implementation constraints
- Treat recorded fixtures as repository artifacts intended for repeatable audit input.
- Fixture structure must support step-by-step evidence, not a single undifferentiated transcript blob.
- Command output and state evidence are both mandatory per audited step because the direction requires both.
- Loader validation must fail closed on incomplete evidence.
- The captured sample fixture must correspond to the exact blocked operator step named in `flow.md`.
- Keep naming/path conventions aligned with existing repo patterns discovered during implementation; do not invent parallel conventions if one already exists.

# References

- Direction: D015 `Provide executable fixtures for operator CLI UX audits`
- Flow reference: `012-persist-direction-status-in-the-database/flow.md` step `1`
- PM decomposition context: fixture-first path; contract before capture before consumption

# Dev Agent Record

## Agent Model Used
- openhands/OpenHands (via agent-sdk)

## Debug Log References
- N/A (all tests pass cleanly)

## Completion Notes List
- Created `factory/testing/fixtures.py`: defines the fixture contract (RecordedFixture, StepEvidence, StateEvidence dataclasses), validation helpers, and `load_audit_fixture()` loader. Loader validates required fields (flow, steps, step number, command, command_output, state_evidence with description and state_snapshot) and fails closed with ValueError on malformed/incomplete input.
- Created `apps/factory/directions/012-persist-direction-status-in-the-database/fixture.json`: sample fixture capturing step 1 of the blocked operator flow (`factory tick --app factory`) with command output and state evidence including direction status, database schema columns, and app identity.
- Created `tests/test_ux_audit_fixtures.py`: 20 automated tests covering valid fixture loading (single step, multi-step, real sample file), flow/step mapping preservation, rejection of missing command_output, rejection of missing state_evidence fields, malformed JSON, and edge cases (null snapshot, empty dict snapshot).
- All 32 UX-audit-related tests pass (20 new + 12 existing).
- No live CLI execution required — fixtures are pure recorded artifacts.

## File List
- `factory/testing/fixtures.py` (new)
- `apps/factory/directions/012-persist-direction-status-in-the-database/fixture.json` (new)
- `tests/test_ux_audit_fixtures.py` (new)

# Senior Developer Review

- Pending

# Review Follow-ups

- Pending