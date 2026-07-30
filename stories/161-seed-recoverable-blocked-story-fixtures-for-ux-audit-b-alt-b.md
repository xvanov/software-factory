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

- [x] UX audit can load a seeded blocked story, advance one tick, and capture before/after status evidence for the revival step.

### Testable Claims (EARS)
AC1.1: WHEN the UX audit loads the seeded blocked-story fixture, THE system SHALL provide a seeded blocked story for the revival scenario
AC1.2: WHEN the UX audit advances runtime by one tick against the seeded blocked-story fixture, THE system SHALL execute the revival step transition
AC1.3: WHEN the UX audit observes the seeded blocked-story fixture before and after the one-tick advance, THE system SHALL make before/after status evidence capturable for the revival step

# Tasks / Subtasks

- [x] Identify the existing test/runtime entrypoint that can load deterministic fixture state
- [x] Add deterministic fixture data for a blocked story paired with already-merged PR state
- [x] Ensure fixture naming/path is stable and audit-invocable
- [x] Add or expose minimal one-tick execution path usable from integration/test context
- [x] Capture pre-tick observable story status from the seeded fixture path
- [x] Capture post-tick observable story status after exactly one tick
- [x] Add an automated integration/smoke test covering load -> tick -> before/after evidence capture
- [x] Verify the fixture path is executable without browser/deploy dependencies
- [x] Record invocation details and evidence surface expected by downstream docs story

# Dev Notes

## Direction acceptance criteria (verbatim)

- [x] UX audit can load a seeded blocked story, advance one tick, and capture before/after status evidence for the revival step.

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
- openhands

## Debug Log References
- `uv run pytest tests/test_audit_revival_fixture.py -q`
- `uv run pytest tests/ -q`

## Completion Notes List
- **Entrypoint identified**: `factory/chain/orchestrator.reconcile_from_github` — the top-of-tick reconciliation pass that detects PR merges out-of-band. It already handles `blocked_ci_unresolved` → `deploy_pending` revival (D013), and the `query_pr_state` injection seam keeps the fixture deterministic and network-free.
- **Fixture module created**: `factory/chain/audit_fixtures.py` — stable, importable module with `seed_blocked_story_db`, `run_one_revival_tick`, `capture_story_evidence`, and `capture_before_after`. Uses canonical slug `audit-fixture-blocked-ci` and PR `#999` so downstream docs can reference a fixed path.
- **One-tick execution**: `run_one_revival_tick` calls `reconcile_from_github` with a `query_pr_state` stub that reports the seeded PR as MERGED — exactly one reconciliation pass, no browser/deploy/network.
- **Evidence capture**: `AuditEvidence` dataclass holds `state_before`, `state_after`, `pr_number`, `error_before`, `error_after`, and `transition_occurred`. `capture_before_after` returns a populated instance after load → capture → tick → capture.
- **No browser/deploy dependencies**: The fixture and test use SQLite + in-process stubs only; zero external dependencies.
- **Tests added**: 6 tests in `tests/test_audit_revival_fixture.py` covering AC1.1 (seed provides blocked story), AC1.2 (one tick executes revival transition), AC1.3 (before/after evidence capturable), full load→tick→evidence path, determinism, and no-browser/no-deploy constraint.

## File List
- `factory/chain/audit_fixtures.py` — new: deterministic fixture module for UX audit
- `tests/test_audit_revival_fixture.py` — new: integration/smoke tests (6 tests)
- `stories/161-seed-recoverable-blocked-story-fixtures-for-ux-audit-b-alt-b.md` — this file

# Senior Developer Review

- TBD

# Review Follow-ups

- TBD