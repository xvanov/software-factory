# Story
## Title
Fix failing required check(s) on main: lint — narrow read

## Description
Prepare a test-first reproduction slice for the post-merge `lint` required check failure on `main`. Scope is limited to identifying the exact lint command/path that fails from repository state or equivalent CI command path, capturing the failure mode in repo-visible regression coverage or deterministic reproduction notes, and leaving the code/config fix to the follow-on story.

## Acceptance Criteria
- [ ] lint passes on sacrifice's main branch

### Testable Claims (EARS)
AC1.1: WHEN the repository's `lint` check is executed against Sacrifice `main` or an equivalent local/CI command path, THE system SHALL complete with a passing result.

## Tasks / Subtasks
- [ ] Identify the canonical `lint` command path used by CI
- [ ] Reproduce the current `lint` failure from repository state or equivalent environment
- [ ] Capture the exact failing tool, file, and rule/output
- [ ] Add or update regression coverage only if the failure mode can be codified in-repo
- [ ] Document deterministic reproduction steps in Dev Agent Record if coverage cannot be codified
- [ ] Verify the reproduction artifact distinguishes current failure from unrelated warnings
- [ ] Do not implement the production fix in this story
- [ ] Hand off exact failure signature to follow-on fix story

## Dev Notes
### Scope notes
- Narrow-read interpretation: this story stops at making the failing `lint` condition explicit and reproducible.
- Follow-on remediation belongs to the separate infra-scoped fix story.
- Direction provides no underlying lint logs beyond an in-progress run notice; treat failure discovery as the primary deliverable.
- No explicit `flow.md` content was provided.
- No explicit `api_spec.md` content was provided.

### flow.md
(none)

### api_spec.md
(none)

### Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Top-level layout]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/modules/backend.md#Section unavailable in provided prelude]
- [Source: context/modules/frontend.md#Section unavailable in provided prelude]
- [Source: context/modules/security.md#Section unavailable in provided prelude]

### Verbatim direction acceptance criteria
- [ ] lint passes on sacrifice's main branch

### Direction evidence to preserve
```text
# Fix failing required check(s) on main: lint

## Why

Post-merge CI-health monitor: the required check(s) lint are failing on sacrifice's main branch AFTER merge (the pre-merge required-check gate is unchanged and remains the primary defense; this is the post-merge safety net). Fix the exact failure below so main goes green again.

=== lint ===
run 29981031391 is still in progress; logs will be available when it is complete
```

### Test-design implications
- The acceptance criterion is end-state only; this story's deliverable is a trustworthy reproduction path that the next story can turn green.
- If no in-repo automated regression can be added without also fixing the defect, record the exact command, environment assumptions, and raw failure output so the Reviewer can validate the handoff.
- Any reproduction artifact must trace directly to the CI `lint` check path, not a guessed local substitute unless equivalence is demonstrated.

## References
- `context/project.md`
- `context/navigation.md`
- `backend/pyproject.toml`
- `frontend/package.json`
- `.github/workflows/` (if present in repo)
- Any repo lint configuration files discovered during implementation

## Dev Agent Record
### Implementation Plan
- Determine which workflow/job defines required `lint`
- Map workflow step to concrete command(s)
- Execute command(s) in repo state matching `main`
- Capture raw failure output verbatim
- Add regression artifact if feasible without landing the fix
- Record exact handoff details for follow-on story

### Commands / Evidence
- To be completed by Dev

### Files Touched
- To be completed by Dev

### Risks / Blockers
- CI logs may be unavailable or ephemeral
- Required `lint` may aggregate multiple tools
- Local reproduction may require toolchain/version parity with CI

## Senior Developer Review
- [ ] Canonical CI `lint` command path identified
- [ ] Reproduction demonstrated from repo state or justified equivalent path
- [ ] Exact failing rule/tool/file captured
- [ ] Regression coverage added, or inability to codify clearly justified
- [ ] No production fix slipped into this story
- [ ] Follow-on story has enough evidence to apply a minimal fix

## Review Follow-ups
- [ ] If CI workflow is ambiguous, resolve the single source of truth for `lint`
- [ ] If multiple lint failures exist, rank by which one blocks required check completion
- [ ] If reproduction depends on environment drift, document versions and pinpoints for the fix story
