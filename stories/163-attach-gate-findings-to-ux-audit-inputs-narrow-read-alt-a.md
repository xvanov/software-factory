# Story

## Title
Attach gate findings to UX audit inputs — narrow read

## Slug
`attach-gate-findings-to-ux-audit-inputs-narrow-read-alt-a`

## Scope
`test`

## Summary
Prepare the reproducible `tests-meaningful` finding artifact fixture the scheduled UX audit input can later consume. Narrow-read scope is limited to creating and verifying the artifact source payload; audit-input wiring is out of scope.

# Acceptance Criteria

- [x] Scheduled UX audit input includes reproducible `tests-meaningful` finding artifacts showing rule id, file, line, and remediation text.

### Testable Claims (EARS)
AC1.1: WHEN the reproducible `tests-meaningful` finding artifact is generated for scheduled UX audit consumption, THE artifact SHALL show rule id.
AC1.2: WHEN the reproducible `tests-meaningful` finding artifact is generated for scheduled UX audit consumption, THE artifact SHALL show file.
AC1.3: WHEN the reproducible `tests-meaningful` finding artifact is generated for scheduled UX audit consumption, THE artifact SHALL show line.
AC1.4: WHEN the reproducible `tests-meaningful` finding artifact is generated for scheduled UX audit consumption, THE artifact SHALL show remediation text.
AC1.5: UNTESTABLE-AS-WRITTEN — the criterion names scheduled UX audit input inclusion, but this narrow-read test story is scoped only to producing the reproducible artifact source, not attaching it to the scheduled audit input.

# Tasks / Subtasks

- [x] Identify the existing `tests-meaningful` output surface used as the reproducible source.
- [x] Add a stable fixture representing a red `tests-meaningful` finding.
- [x] Ensure the fixture exposes rule id.
- [x] Ensure the fixture exposes file.
- [x] Ensure the fixture exposes line.
- [x] Ensure the fixture exposes remediation text.
- [x] Add/extend tests that verify fixture generation or loading is reproducible.
- [x] Add/extend tests that verify the artifact field set is complete.
- [x] Confirm artifact shape is suitable for later scheduled UX audit input attachment.
- [x] Do not wire the scheduled UX audit input in this story.

# Dev Notes

## Scope Notes
- Narrow-read interpretation: satisfy the direction by establishing the reproducible `tests-meaningful` finding artifact fixture only.
- Excluded from this story: scheduled UX audit input attachment logic, operator docs updates.
- Because the repo prelude provided no canonical context files, there are no valid `[Source: ...]` pointers to include in this story.

## flow.md (verbatim embed)

# User flow

1. Flow: 014-detect-tests-that-bypass-the-app-entry-point/flow.md
2. Step: 2
3. Evidence: Step requires observing PR gate output (`tests-meaningful` red) naming file and line, but current invocation is `text_run` with no CI/PR surface, browser access, or captured gate artifact attached to the prompt.
4. Suggestion: Expose CI finding artifacts or a reproducible local gate command output to the audit so message clarity can be checked against the documented expectation.

## api_spec.md (verbatim embed)

(none)

## Direction Acceptance Criteria (verbatim embed)

- [ ] Scheduled UX audit input includes reproducible `tests-meaningful` finding artifacts showing rule id, file, line, and remediation text.

## Implementation Constraints
- Preserve exact required fields from direction: rule id, file, line, remediation text.
- Prefer deterministic fixture content over live CI-only capture.
- If the current `tests-meaningful` output is text-only, add the minimal parser/normalizer needed for reproducible assertions.
- Keep artifact production isolated so the backend story can consume it without redefining field semantics.
- If no explicit fixture convention exists, follow the nearest existing test-fixture pattern in the codebase.

## Gaps / Reviewer Attention
- Direction AC validates end-to-end inclusion in scheduled UX audit input; this story only establishes the reproducible artifact source needed for that downstream integration.
- If the existing gate output does not already contain remediation text, reviewer should flag mismatch instead of allowing invented content.

# References

- Direction: `D017 attach gate findings to UX audit inputs`
- PM child-story context: `D017 add reproducible tests-meaningful finding artifact fixture`
- Related flow reference named by direction: `014-detect-tests-that-bypass-the-app-entry-point/flow.md` step `2`

# Dev Agent Record

## Agent Model Used
- openhands (claude-sonnet-4)

## Debug Log References
- `uv run pytest -q`

## Completion Notes
- Added `make_tests_meaningful_fixture_finding()` to `factory/chain/slop_detector.py` as a deterministic fixture source that always returns a red `tests-meaningful` `SlopFinding`.
- Fixture payload exposes the required fields for downstream UX-audit attachment work via the existing finding schema: rule id (`kind`), file (`path`), line (`line`), and remediation text (`why_slop`).
- Added 7 tests in `tests/test_ux_auditor_input.py` to verify AC1.1–AC1.4 plus reproducibility, complete field coverage, and JSON-safe artifact serialization.
- Scope stayed narrow-read: no scheduled UX audit input attachment logic was added in this story.
- Full test suite is green after dependency sync (`uv sync --all-extras`; `uv run pytest -q`).

## File List
- `factory/chain/slop_detector.py` — added `make_tests_meaningful_fixture_finding()` and sentinel constants
- `tests/test_ux_auditor_input.py` — added 7 tests for the tests-meaningful fixture artifact

# Senior Developer Review

- [ ] Scope stayed within reproducible artifact production.
- [ ] Artifact is reproducible without CI/PR-only dependencies.
- [ ] Artifact visibly contains rule id.
- [ ] Artifact visibly contains file.
- [ ] Artifact visibly contains line.
- [ ] Artifact visibly contains remediation text.
- [ ] No audit-input attachment logic slipped into this story.
- [ ] Any missing remediation/source-field data was flagged, not fabricated.

# Review Follow-ups

- [ ] If artifact shape differs from current audit-input expectations, align in the backend attachment story.
- [ ] If fixture generation depends on brittle output formatting, harden parser/normalizer before merge.
- [ ] If remediation text is absent upstream, escalate as an AC gap against the direction.