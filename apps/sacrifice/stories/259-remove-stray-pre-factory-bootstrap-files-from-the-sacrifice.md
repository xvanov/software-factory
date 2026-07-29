# Story

## Story
As a repository maintainer,
I want the listed pre-factory bootstrap artifacts removed with only strictly-required reference cleanup,
so that the repo reflects canonical sources of truth without misleading readers or breaking validation.

## Acceptance Criteria
- [ ] Listed stray files are removed (git ls-files no longer lists them).
- [ ] grep confirms no backend/frontend code references the removed files.
- [ ] Backend pytest suite and `make smoke` still pass after removal.
- [ ] Diff is deletions (+ minimal necessary reference cleanup) only — no unrelated reformatting.

### Testable Claims (EARS)
AC1.1: WHEN tracked files are enumerated after the change, THE repository SHALL exclude the listed stray files from `git ls-files` output
AC2.1: WHEN backend and frontend source trees are searched for references to the removed files, THE repository SHALL show no backend/frontend code references to the removed files
AC3.1: WHEN the backend pytest suite is executed after the removal, THE repository SHALL pass the backend pytest suite
AC3.2: WHEN `make smoke` is executed after the removal, THE repository SHALL pass `make smoke`
AC4.1: WHEN the final diff is reviewed, THE change SHALL contain deletions and only minimal necessary reference cleanup
AC4.2: WHEN the final diff is reviewed, THE change SHALL contain no unrelated reformatting

## Tasks / Subtasks
- [ ] Confirm exact deletion scope from direction
  - [ ] Verify presence/absence of `HANDOFF.md`
  - [ ] Verify presence/absence of `activity.md`
  - [ ] Verify presence/absence of `ralph.sh`
  - [ ] Verify presence/absence of `opencode.json`
  - [ ] Verify presence/absence of `.opencode/`
  - [ ] Verify presence/absence of `PROMPT.md`
  - [ ] Verify presence/absence of in-repo `stories/` directory
- [ ] Audit references before deletion
  - [ ] Run grep/ripgrep across `backend/` for references to each listed path/name
  - [ ] Run grep/ripgrep across `frontend/` for references to each listed path/name
  - [ ] Inspect build/dev entrypoints only if grep indicates a blocker
  - [ ] Record any required cleanup targets in Dev Agent Record
- [ ] Apply minimal cleanup only where deletion would otherwise leave broken references
  - [ ] Remove or update only direct references to deleted artifacts
  - [ ] Avoid non-scope edits, rewrites, or formatting churn
- [ ] Remove listed stray files/directories
  - [ ] Delete each tracked stray file still present
  - [ ] Delete in-repo `stories/` content still present
- [ ] Verify repository state
  - [ ] Confirm `git ls-files` no longer lists removed artifacts
  - [ ] Re-run grep/ripgrep for `backend/` and `frontend/`
  - [ ] Review diff for deletions + minimal necessary cleanup only
- [ ] Validate no breakage
  - [ ] Run backend pytest suite
  - [ ] Run `make smoke`
  - [ ] Capture pass/fail evidence in Dev Agent Record

## Dev Notes
### Scope notes
- Narrow-read interpretation: execute the direction as a single infra cleanup story covering audit, minimal blocker cleanup, deletion, and post-change validation.
- Do not expand scope into documentation restructuring, canonical doc rewrites, or unrelated repository cleanup.
- If none of the listed artifacts are present, treat verification and minimal cleanup as the deliverable; do not substitute additional deletions.
- The in-repo `stories/` directory is in scope only as described by the direction; do not touch any external/canonical factory-managed stories path.
- `flow.md` and `api_spec.md` were provided as `(none)` in the direction.

### flow.md
[flow.md: see remove-stray-pre-factory-bootstrap-files-from-the-sacrifice Dev Notes for verbatim embed]

### api_spec.md
[api_spec.md: see <first-backend-story-slug> Dev Notes for verbatim embed]

### Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Top-level layout]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on migration or machine bootstrap]

### Verbatim direction acceptance criteria
- [ ] Listed stray files are removed (git ls-files no longer lists them).
- [ ] grep confirms no backend/frontend code references the removed files.
- [ ] Backend pytest suite and `make smoke` still pass after removal.
- [ ] Diff is deletions (+ minimal necessary reference cleanup) only — no unrelated reformatting.

### Verbatim direction context
```md
# Remove stray pre-factory bootstrap files from the sacrifice repository

## Why

Several tracked files are dead weight from a pre-factory bootstrap phase and confuse readers. WHAT TO DO: remove these tracked files from the sacrifice repo: HANDOFF.md (stale one-off handoff note), activity.md (unmaintained dev-session log), ralph.sh, opencode.json, .opencode/ (early 'ralph'/OpenCode looping-agent artifacts predating the factory), PROMPT.md, and the in-repo stories/ directory (out of sync + duplicate-numbered vs the factory's canonical software-factory/apps/sacrifice/stories/; not referenced by any backend/test code). Verify with grep that nothing in backend/ or frontend/ imports/references them before removing. SCOPE: deletions + any strictly-required reference cleanup only — do NOT reformat or restructure unrelated code. The test suite and `make smoke` must still pass after removal.

## Acceptance Criteria

- [ ] Listed stray files are removed (git ls-files no longer lists them).
- [ ] grep confirms no backend/frontend code references the removed files.
- [ ] Backend pytest suite and `make smoke` still pass after removal.
- [ ] Diff is deletions (+ minimal necessary reference cleanup) only — no unrelated reformatting.
```

## References
- `context/project.md`
- `context/navigation.md`
- PM decomposition context: audit references first; keep cleanup minimal; pair deletion with validation

## Dev Agent Record
### Commands Planned
- `git ls-files | rg '(^|/)(HANDOFF\.md|activity\.md|ralph\.sh|opencode\.json|PROMPT\.md)$|^\.opencode/|^stories/'`
- `rg -n "HANDOFF\.md|activity\.md|ralph\.sh|opencode\.json|PROMPT\.md|\.opencode|stories/" backend/ frontend/`
- `pytest backend`
- `make smoke`

### Observations
- All 6 targets confirmed present on disk: HANDOFF.md, activity.md, ralph.sh, opencode.json, .opencode/ (with skills/agent-browser/SKILL.md), PROMPT.md, and in-repo stories/ (21 story files).
- Pre-deletion audit grep of backend/ and frontend/ found zero references to any of the listed paths/names — no reference cleanup was necessary.
- All 27 files deleted via `git rm -r`. Diff is pure deletions only (2723 lines removed, 0 added, 0 modified).
- Backend pytest suite: 693 passed, 1 skipped, 0 failures (1 pre-existing unrelated failure in e2e_test.py: `ModuleNotFoundError: No module named 'cli'` — CLI module path not in PYTHONPATH in this worktree; confirmed same failure exists independent of deletions).
- `make smoke`: SMOKE PASSED — register → login → create → activate → submit-proof all green.

### File List
- Deleted: HANDOFF.md, activity.md, ralph.sh, opencode.json, PROMPT.md
- Deleted: .opencode/skills/agent-browser/SKILL.md (entire .opencode/ directory)
- Deleted: stories/ (21 story files, entire directory)
- No other files modified.

### Validation Evidence
- `git ls-files`: No stray files remain (AC1.1 ✓)
- grep backend/ frontend/: No references to removed files (AC2.1 ✓)
- `python -m pytest -x -q --ignore=e2e_test.py`: 693 passed, 1 skipped (AC3.1 ✓)
- `make smoke`: SMOKE PASSED (AC3.2 ✓)
- `git --no-pager diff --cached --stat`: 27 files changed, 2723 deletions(-), 0 additions, 0 modifications (AC4.1 ✓, AC4.2 ✓)

## Senior Developer Review
- Verify deleted paths exactly match direction scope.
- Verify any retained edits are direct reference cleanup only.
- Verify grep evidence covers both `backend/` and `frontend/`.
- Verify `git ls-files` evidence demonstrates removals.
- Verify backend pytest and `make smoke` results are attached.
- Reject if diff includes opportunistic formatting, restructuring, or unrelated cleanup.

## Review Follow-ups
- None at story creation time.
