# Story

## Title
Attach gate findings to UX audit inputs — broad read

## Slug
`attach-gate-findings-to-ux-audit-inputs-broad-read-alt-b`

## Scope
`test`

## Summary
Prepare the reproducible `tests-meaningful` finding artifact path that scheduled UX audit input can consume, with test-facing coverage over artifact fields and audit-input inclusion behavior.

# Acceptance Criteria

- [ ] Scheduled UX audit input includes reproducible `tests-meaningful` finding artifacts showing rule id, file, line, and remediation text.

### Testable Claims (EARS)
AC1.1: WHEN the scheduled UX audit input is generated, THE audit input SHALL include reproducible `tests-meaningful` finding artifacts
AC1.2: WHEN a `tests-meaningful` finding artifact is included in scheduled UX audit input, THE artifact SHALL show rule id
AC1.3: WHEN a `tests-meaningful` finding artifact is included in scheduled UX audit input, THE artifact SHALL show file
AC1.4: WHEN a `tests-meaningful` finding artifact is included in scheduled UX audit input, THE artifact SHALL show line
AC1.5: WHEN a `tests-meaningful` finding artifact is included in scheduled UX audit input, THE artifact SHALL show remediation text

# Tasks / Subtasks

- [ ] Identify the existing scheduled UX audit input assembly path exercised by this direction
- [ ] Identify the current `tests-meaningful` finding source or nearest reproducible fixture seam
- [ ] Add or update a reproducible test fixture for `tests-meaningful` findings containing rule id, file, line, and remediation text
- [ ] Add test coverage asserting the fixture output remains reproducible across runs
- [ ] Add test coverage asserting scheduled UX audit input includes the finding artifact payload
- [ ] Add test coverage asserting the included artifact exposes rule id, file, line, and remediation text
- [ ] Keep implementation scope limited to test-enabling and verification changes needed for audit-input attachment behavior
- [ ] Record exact file paths and commands used in Dev Agent Record

# Dev Notes

## Flow Embed

# User flow

1. Flow: 014-detect-tests-that-bypass-the-app-entry-point/flow.md
2. Step: 2
3. Evidence: Step requires observing PR gate output (`tests-meaningful` red) naming file and line, but current invocation is `text_run` with no CI/PR surface, browser access, or captured gate artifact attached to the prompt.
4. Suggestion: Expose CI finding artifacts or a reproducible local gate command output to the audit so message clarity can be checked against the documented expectation.

## API Spec Embed

(none)

## Context Pointers

- No canonical context files were provided in this invocation.
- No `context/project.md` available.
- No `context/navigation.md` available.
- No `context/current-state.md` available.
- No `context/modules/*.md` files available.
- Dev must derive file-level implementation context from the repository code paths that contain scheduled UX audit input assembly and `tests-meaningful` gate output generation.
- Test-Designer should inspect the same implementation paths and any existing fixtures covering audit-input prompts, gate findings, or text-run payload assembly.

## Direction Acceptance Criteria (Verbatim)

- [ ] Scheduled UX audit input includes reproducible `tests-meaningful` finding artifacts showing rule id, file, line, and remediation text.

## Direction/PM Alignment Notes

- PM decomposition context indicates this story is the first test-scoped slice: "Add a reproducible artifact producer for `tests-meaningful` findings that captures the required fields."
- This broad-read story must still validate the end requirement against scheduled UX audit input, not only fixture shape in isolation.
- `api_spec.md` is explicitly `(none)` in the direction.
- Because no canonical repo context was supplied, any ambiguity discovered in artifact source, audit-input builder, or fixture format must be surfaced explicitly in implementation notes and review.

# References

- `direction.md` — Attach gate findings to UX audit inputs
- `flow.md` — embedded verbatim in Dev Notes
- `api_spec.md` — `(none)`
- PM tracker title: `D017 attach gate findings to UX audit inputs`
- PM child story context: `D017 add reproducible tests-meaningful finding artifact fixture`

# Dev Agent Record

## Agent Model Used
- openhands

## Debug Log References
- `python -m pytest tests/test_ux_auditor_input.py -v` — 20/20 pass
- `python -m pytest tests/ --ignore=tests/test_cli_audit.py --ignore=tests/test_cli_tui.py --ignore=tests/test_ears_property_oracle.py --ignore=tests/test_runner_azure.py --ignore=tests/test_runner_cached_tokens.py --ignore=tests/test_settings_audit.py -q` — all green (3 skipped, pre-existing)
- Pre-existing failures confirmed before implementation: `test_audit_flags_estimated_cache_rate_spend`, `test_property_oracle_fails_on_violation_even_when_dev_tests_green`, all 9 Azure/runner/settings_audit failures

## Completion Notes List
- Added `_collect_tests_meaningful_findings(app, software_factory_root)` at line 749 of `factory/chain/scheduled_tasks.py`. It scans `apps/<app>/repo/test_*.py` files using `factory.chain.slop_detector.scan_file` and returns a list of `SlopFinding.as_dict()` payloads. Collection is deterministic (sorted rglob) and best-effort (exceptions are swallowed with `# noqa: BLE001`).
- Wired the new collector into `_build_ux_auditor_context` (line 811-830) as a new `### Gate Findings` section that appears after Flow Artifacts and before App URL Context. When findings exist, each is rendered with rule id (`kind`), file (`path`), line, and remediation (`why_slop`). When none exist, a note is included instead.
- Added 10 new tests in `tests/test_ux_auditor_input.py` covering: fixture existence, reproducibility, empty-no-slop case, audit input inclusion (section header + payload), graceful handling when no repo dir exists, and individual field assertions (kind, path, line, why_slop).
- Pre-existing test failures confirmed unrelated: `test_cli_audit.py`, `test_cli_tui.py`, `test_ears_property_oracle.py`, `test_runner_azure.py`, `test_runner_cached_tokens.py`, `test_settings_audit.py` — all fail identically on the base commit.

## File List
- `factory/chain/scheduled_tasks.py` — added `_collect_tests_meaningful_findings` function and wired it into `_build_ux_auditor_context`
- `tests/test_ux_auditor_input.py` — added 10 tests (helper + 9 functional) for D017 gate-findings attachment
- `stories/164-attach-gate-findings-to-ux-audit-inputs-broad-read-alt-b.md` — this file, Dev Agent Record

# Senior Developer Review

- [ ] Story scope stayed within `test`
- [ ] Reproducible artifact source identified and exercised by tests
- [ ] Scheduled UX audit input inclusion verified by tests
- [ ] Artifact fields verified: rule id, file, line, remediation text
- [ ] No requirements added beyond direction AC
- [ ] Any missing repository context captured explicitly

# Review Follow-ups

- [ ] TBD