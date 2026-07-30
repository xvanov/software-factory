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

- [ ] Define fixture contract for recorded CLI audit evidence.
  - [ ] Specify required fields for per-step command output.
  - [ ] Specify required fields for per-step state evidence.
  - [ ] Specify representation for flow identity and step identity.
  - [ ] Specify failure behavior for malformed or incomplete fixtures.
- [ ] Add sample loader or reader for the fixture contract.
  - [ ] Load fixture data from repository path(s) intended for audit inputs.
  - [ ] Validate required fields before exposing fixture contents.
  - [ ] Return deterministic structure for downstream audit consumers.
- [ ] Capture one sample fixture for the blocked operator step referenced by D015.
  - [ ] Record `factory tick --app factory` command evidence.
  - [ ] Record corresponding state inspection evidence.
  - [ ] Tie evidence to flow `012-persist-direction-status-in-the-database/flow.md`, step `1`.
- [ ] Add automated tests for contract and loader behavior.
  - [ ] Valid fixture loads successfully.
  - [ ] Missing command output is rejected.
  - [ ] Missing state evidence is rejected.
  - [ ] Flow/step mapping is preserved.
- [ ] Keep implementation fixture-first.
  - [ ] Do not require live CLI execution in this story.
  - [ ] Do not broaden scope into audit runtime consumption beyond proving loader readiness.

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
- No `context/project.md` available.
- No `context/navigation.md` available.
- No module files available.
- Dev/Test-Designer must derive repository-specific paths and naming from the codebase on implementation.

## Implementation constraints
- Treat recorded fixtures as repository artifacts intended for repeatable audit input.
- Fixture structure must support step-by-step evidence, not a single undifferentiated transcript blob.
- Command output and state evidence are both mandatory per audited step because the direction requires both.
- Loader validation must fail closed on incomplete evidence.
- The captured sample fixture must correspond to the exact blocked operator step named in `flow.md`.
- Keep naming/path conventions aligned with existing repo patterns discovered during implementation; do not invent parallel conventions if one already exists.

## Open questions to resolve from codebase
- Existing location, if any, for UX audit inputs or fixtures.
- Existing test helpers for loading structured artifacts.
- Existing schema/validation utilities suitable for fixture contract enforcement.
- Existing references to D012 audit flow and current audit runtime entrypoints.

# References

- Direction: D015 `Provide executable fixtures for operator CLI UX audits`
- Flow reference: `012-persist-direction-status-in-the-database/flow.md` step `1`
- PM decomposition context: fixture-first path; contract before capture before consumption

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

- Pending

# Review Follow-ups

- Pending
