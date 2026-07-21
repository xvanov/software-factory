# Story

## Title
Gate UX audits on available flow artifacts — broad read

## Slug
`gate-ux-audits-on-available-flow-artifacts-broad-read-alt-b`

## Scope
`backend`

## Summary
Implement the backend guard and payload contract for replay-based UX auditing so runs do not proceed without at least one available `flow.md` artifact and, when they do proceed, the invocation payload includes at least one `flow.md` path plus contents.

# Acceptance Criteria

- [x] UX auditor run is skipped or marked not-applicable when zero flow.md files are available.
- [x] Invocation payload includes at least one flow.md path and contents before replay-based auditing runs.

### Testable Claims (EARS)
AC1.1: WHEN replay-based UX auditing is requested, GIVEN zero `flow.md` files are available, THE UX auditor run SHALL be skipped or marked not-applicable.
AC2.1: WHEN replay-based UX auditing runs, THE invocation payload SHALL include at least one `flow.md` path.
AC2.2: WHEN replay-based UX auditing runs, THE invocation payload SHALL include contents for at least one `flow.md`.

# Tasks / Subtasks

- [x] Identify the backend decision point that launches or classifies replay-based UX auditor runs.
- [x] Implement flow-artifact presence detection for available `flow.md` files in invocation context.
- [x] Gate replay-based UX auditing when zero `flow.md` files are available.
- [x] Ensure gated outcome is represented as skipped or not-applicable at the existing run/classification boundary.
- [x] Update UX audit payload assembly to include at least one `flow.md` artifact path.
- [x] Update UX audit payload assembly to include corresponding `flow.md` contents.
- [x] Preserve existing replay-based UX auditing behavior when one or more `flow.md` files are available.
- [x] Add automated tests for zero-flow gating behavior.
- [x] Add automated tests proving payload contains at least one `flow.md` path and contents before replay-based auditing runs.
- [x] Verify no replay-based UX audit executes on the zero-flow path.

# Dev Notes

## Scope Notes
- Broad-read story covers both declared acceptance criteria in one backend slice.
- `flow.md` artifact naming in this direction refers to available flow files in invocation context; implement against the repository's existing artifact discovery and payload-building conventions.
- If the codebase distinguishes between "skip" and "not-applicable", use the status already recognized by the UX auditing pipeline; do not invent a new terminal state unless required by existing architecture.
- If no explicit `flow.md` artifact metadata structure exists, extend the existing invocation payload shape minimally and consistently with current artifact serialization patterns.

## flow.md
[flow.md not provided in direction]

## api_spec.md
[api_spec.md not provided in direction]

## Context Pointers
- No canonical context files were provided in this invocation (`context/project.md`, `context/navigation.md`, module files unavailable).
- Build implementation context from the backend code paths that currently: discover direction sibling artifacts, assemble persona invocation payloads, and trigger/classify UX auditor execution.

## Verbatim Direction Acceptance Criteria
- [x] UX auditor run is skipped or marked not-applicable when zero flow.md files are available.
- [x] Invocation payload includes at least one flow.md path and contents before replay-based auditing runs.

# References

- Direction: `D011 gate UX audits on available flow artifacts`
- PM tracker title: `D011 gate UX audits on available flow artifacts`
- PM decomposition context:
  - `D011 skip or mark UX replay audit N/A without flow.md`
  - `D011 include flow.md path and contents in UX audit payload`

# Dev Agent Record

## Implementation Notes
- Both acceptance criteria were already satisfied by prior stories:
  - AC1 (gating): implemented in narrow-read story #89 via the gate in `run_scheduled_persona` (`factory/chain/scheduled_tasks.py` lines 592-605). When `persona == "ux_auditor"` and `_collect_flow_artifacts` returns empty, the run records `status="rejected"` with `error="ux_auditor_no_flow_artifacts"` before any LLM call.
  - AC2 (payload): implemented in story #78 via `_build_ux_auditor_context` which assembles flow.md path + contents into the invocation prompt, called from `_live_run` for `ux_auditor` persona.
- This broad-read story adds integration-level tests proving both ACs work together through the public `run_scheduled_persona` entry point, plus coverage for multiple flow.md artifacts.
- Decision point: `run_scheduled_persona` in `factory/chain/scheduled_tasks.py`.
- Flow-artifact presence detection: `_collect_flow_artifacts(app, root)` scans `<root>/apps/<app>/directions/*/flow.md`.
- Gated outcome: `status="rejected"`, `error="ux_auditor_no_flow_artifacts"` — uses the existing `"rejected"` status already recognized by the pipeline.
- Payload assembly: `_build_ux_auditor_context` produces `## Scheduled UX Audit Runtime Inputs` section with `### Flow Artifacts` subsection containing each `{direction-id}/flow.md` label and full contents.

## Files Touched
- `factory/chain/scheduled_tasks.py` — gate + payload assembly (pre-existing from stories #89 and #78)
- `tests/test_ux_auditor_input.py` — added 4 tests for broad-read integration coverage

## Test Evidence
- `test_collect_flow_artifacts_returns_filename_and_steps` — single flow.md path + contents
- `test_collect_flow_artifacts_returns_multiple_flow_files` — multiple flow.md files all collected
- `test_build_context_requires_at_least_one_flow_artifact` — ValueError on zero flow.md
- `test_build_context_includes_app_url_context` — app URL in payload
- `test_build_context_includes_runtime_context_fields` — runtime context in payload
- `test_build_context_includes_multiple_flow_artifacts` — multiple flow.md paths + contents in context
- `test_live_run_ux_prompt_contains_flow_and_runtime_inputs` — path + contents in _live_run prompt
- `test_live_run_non_ux_prompt_is_unchanged` — non-UX personas unaffected
- `test_run_scheduled_persona_skips_when_ux_live_run_has_no_flow_artifact` — zero-flow gating (AC1.1)
- `test_run_scheduled_persona_no_flow_triggers_no_text_run` — text_run never called on zero-flow (AC1.1)
- `test_run_scheduled_persona_payload_includes_flow_path_and_contents` — path + contents through public entry point (AC2.1 + AC2.2)
- `test_live_run_is_not_blocked_when_flow_md_is_available` — normal path preserved
- `test_dry_run_does_not_require_flow_md_artifacts` — dry-run not gated
- `test_file_finding_creates_flow_md_for_ux_finding` — flow.md in filed findings
- `test_ux_auditor_dry_run_files_friction_direction` — dry-run fixture
- `test_ux_auditor_rate_limit_zero_refuses` — rate limit gate

# Senior Developer Review

- Pending.

# Review Follow-ups

- Pending.