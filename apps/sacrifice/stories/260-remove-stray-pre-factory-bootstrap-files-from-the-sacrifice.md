# Story

## Story
As a maintainer,
I want the repository purged of stale pre-factory bootstrap artifacts with only strictly-required reference cleanup,
so that the repo reflects canonical sources of truth without misleading readers or breaking validation paths.

## Acceptance Criteria
- [ ] Listed stray files are removed (git ls-files no longer lists them).
- [ ] grep confirms no backend/frontend code references the removed files.
- [ ] Backend pytest suite and `make smoke` still pass after removal.
- [ ] Diff is deletions (+ minimal necessary reference cleanup) only — no unrelated reformatting.

### Testable Claims (EARS)
AC1.1: WHEN the repository tracked-file list is checked after the change, THE repository SHALL no longer list the direction-specified stray files/directories.
AC2.1: WHEN a grep audit is run against backend/ and frontend/ after the change, THE codebase SHALL show no references to the removed files.
AC3.1: WHEN the backend pytest suite is run after the change, THE repository SHALL pass the backend pytest suite.
AC3.2: WHEN `make smoke` is run after the change, THE repository SHALL pass `make smoke`.
AC4.1: WHEN the final diff is reviewed, THE change SHALL consist of deletions plus only minimal necessary reference cleanup.
AC4.2: WHEN the final diff is reviewed, THE change SHALL include no unrelated reformatting.

## Tasks / Subtasks
- [ ] Audit tracked presence of all direction-listed artifacts.
  - [ ] Confirm current presence/absence via `git ls-files` for `HANDOFF.md`.
  - [ ] Confirm current presence/absence via `git ls-files` for `activity.md`.
  - [ ] Confirm current presence/absence via `git ls-files` for `ralph.sh`.
  - [ ] Confirm current presence/absence via `git ls-files` for `opencode.json`.
  - [ ] Confirm current presence/absence via `git ls-files` for `.opencode/`.
  - [ ] Confirm current presence/absence via `git ls-files` for `PROMPT.md`.
  - [ ] Confirm current presence/absence via `git ls-files` for in-repo `stories/`.
- [ ] Audit references before deletion.
  - [ ] Run grep over `backend/` for each listed path/name.
  - [ ] Run grep over `frontend/` for each listed path/name.
  - [ ] Identify non-backend/non-frontend references that must be minimally cleaned to permit safe deletion.
- [ ] Remove stray artifacts.
  - [ ] Delete each listed tracked file still present.
  - [ ] Delete `.opencode/` if tracked.
  - [ ] Delete in-repo `stories/` if tracked.
- [ ] Apply minimal cleanup only where deletion creates a real blocker.
  - [ ] Update/remove direct references made invalid by deletion.
  - [ ] Avoid restructuring, wording churn, or formatting-only edits.
- [ ] Validate repository state.
  - [ ] Re-run `git ls-files` to confirm removed items no longer appear.
  - [ ] Re-run grep over `backend/` and `frontend/` to confirm no references remain.
  - [ ] Run backend pytest suite.
  - [ ] Run `make smoke`.
  - [ ] Review diff for deletions + minimal necessary cleanup only.

## Dev Notes
### Scope notes
- Broad-read story covers both PM slices in one issue-sized implementation: audit, minimal blocker cleanup, deletion, and validation.
- Direction permits deletions plus strictly-required reference cleanup only.
- In-repo `stories/` referenced here means the repository-local directory described in the direction, not the factory-managed output location used by the chain.
- If any listed artifact is already absent from the worktree, treat that as no-op for deletion but still validate that tracked files and references satisfy the acceptance criteria.

### flow.md
[flow.md: see remove-stray-pre-factory-bootstrap-files-from-the-sacrifice Dev Notes for verbatim embed]

### api_spec.md
[api_spec.md: see <first-backend-story-slug> Dev Notes for verbatim embed]

### Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Top-level layout]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#Navigation]

### Verbatim direction acceptance criteria
- [ ] Listed stray files are removed (git ls-files no longer lists them).
- [ ] grep confirms no backend/frontend code references the removed files.
- [ ] Backend pytest suite and `make smoke` still pass after removal.
- [ ] Diff is deletions (+ minimal necessary reference cleanup) only — no unrelated reformatting.

### Verbatim direction flow.md
(none)

### Verbatim direction api_spec.md
(none)

## References
- Direction: `direction.md`
- PM decomposition context: `pm_result.child_stories`
- Canonical story template: `factory/artifacts/story_template.md`
- Validation commands named by direction: backend pytest suite, `make smoke`, `git ls-files`, grep over `backend/` and `frontend/`

## Dev Agent Record
### Agent Model Used
- TBD

### Debug Log References
- TBD

### Completion Notes List
- TBD

### File List
- TBD

## Senior Developer Review
- TBD

## Review Follow-ups
- TBD
