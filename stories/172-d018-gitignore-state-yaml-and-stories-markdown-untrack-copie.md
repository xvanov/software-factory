# Story

## Title
D018 gitignore state.yaml and stories markdown, untrack copies

## Slug
`d018-gitignore-state-yaml-and-stories-markdown-untrack-copie`

## Scope
`infra`

## Summary
Change repo tracking semantics so machine-written direction `state.yaml` projections and rendered story markdown remain written on disk but are ignored by git, and remove already-committed copies from tracking in the same change.

# Acceptance Criteria

- `apps/*/directions/*/state.yaml` is gitignored, and `git status` is clean immediately after a tick that changes a direction's status.
- `apps/*/stories/*.md` is gitignored, and `git status` is clean immediately after a tick that spawns or advances a story.
- Both are still WRITTEN to disk, so an operator can read them without querying the database.
- The already-committed copies are removed from tracking in the same change, so the working tree stops showing them as modified.

### Testable Claims (EARS)
AC1.1: WHEN a tick changes a direction's status, THE repository SHALL treat `apps/*/directions/*/state.yaml` as gitignored
AC1.2: WHEN a tick changes a direction's status, THE `git status` result SHALL be clean immediately after the tick
AC2.1: WHEN a tick spawns or advances a story, THE repository SHALL treat `apps/*/stories/*.md` as gitignored
AC2.2: WHEN a tick spawns or advances a story, THE `git status` result SHALL be clean immediately after the tick
AC3.1: WHEN machine-written direction state is updated, THE system SHALL still write `apps/*/directions/*/state.yaml` to disk
AC3.2: WHEN story output is spawned or advanced, THE system SHALL still write `apps/*/stories/*.md` to disk
AC3.3: WHEN an operator inspects the app tree, THE operator SHALL be able to read both artifact types without querying the database
AC4.1: WHEN this change is applied, THE repository SHALL remove already-committed copies of the targeted machine-written artifacts from tracking in the same change
AC4.2: WHEN the targeted machine-written artifacts are no longer tracked, THE working tree SHALL stop showing them as modified

# Tasks / Subtasks

- [x] Update ignore rules for machine-written artifacts
  - [x] Ignore `apps/*/directions/*/state.yaml`
  - [x] Ignore `apps/*/stories/*.md`
  - [x] Do not ignore `direction.md`, `flow.md`, `api_spec.md`, or `artifacts/`
  - [x] Do not ignore `apps/<app>/context/*.md`
- [x] Remove currently tracked copies from git index
  - [x] Untrack committed `apps/*/directions/*/state.yaml`
  - [x] Untrack committed `apps/*/stories/*.md`
  - [x] Preserve files on disk while removing from tracking
- [x] Verify repo-boundary behavior after change
  - [x] Confirm a tick-updated `state.yaml` does not dirty `git status`
  - [x] Confirm a tick-written story markdown file does not appear as untracked
  - [x] Confirm both artifact types still exist on disk after tick activity
- [x] Guard scope boundaries
  - [x] Leave regeneration command work to follow-on story
  - [x] Leave backfill compatibility work to follow-on story
  - [x] Leave git-clean regression test implementation to follow-on story

# Dev Notes

## flow.md

# Operator flow — a tree that stays clean

1. **Start from a clean tree.** The operator runs `git status` and sees nothing
   pending.

2. **Run a tick that changes state.** `factory tick --app factory` advances a
   story and transitions a direction.

3. **Check the tree again.** `git status` is still clean. Today this step shows
   modified `state.yaml` files and untracked `stories/*.md`.

4. **Read the state anyway.** The operator opens
   `apps/factory/directions/<id>/state.yaml` and reads the current status, without
   querying the database — the file is still written, just not tracked.

5. **Simulate a fresh clone.** The operator clones the repo somewhere new and sees
   no `state.yaml` and no `stories/*.md`.

6. **Reconstruct them.** The operator runs the regenerate command and sees every
   direction's `state.yaml` written from the database, with statuses matching the
   source repo — and `git status` in the clone is still clean afterwards.

7. **Confirm a hand-written direction still works.** The operator writes a new
   direction directory by hand in the clone, runs `factory directions-backfill`,
   and sees it imported rather than ignored.

## api_spec.md

[api_spec.md: see <first-backend-story-slug> Dev Notes for verbatim embed]

## Story-specific implementation notes

- This story covers only the repo-boundary slice: ignore patterns and tracked-file removal.
- The acceptance criteria above include later-slice outcomes; implementation here must not block them.
- Because this is an `infra` story, embed the flow once here and cross-reference `api_spec.md` instead of embedding `(none)`.
- Open question from direction remains unresolved here unless required by implementation: regeneration command shape belongs to the follow-on backend story.

# References

- Direction: tracker title `D018 stop tracking machine-written direction/story state`
- PM decomposition: child story `D018 gitignore state.yaml and stories markdown, untrack copies`
- Direction source sections: `Why`, `What`, `Acceptance Criteria`, `Out of scope`, `Open questions`

# Dev Agent Record

## Status
Complete

## Agent Notes
- Updated `.gitignore` with two new rule blocks: `apps/*/directions/*/state.yaml` and `apps/*/stories/*.md`, placed after the existing `artifacts/**` block.
- Removed from tracking (git rm --cached): 91 `state.yaml` files and 132 `stories/*.md` files. All remain on disk.
- Guarded scope boundaries: `direction.md`, `flow.md`, `api_spec.md` remain tracked (no glob matches them). `apps/<app>/context/*.md` paths are deeper than the new globs and unaffected.
- Existing `artifacts/**` ignore rule and its `.gitkeep` exception are unchanged.

## File List
- `.gitignore` — added two ignore-pattern blocks
- `tests/test_gitignore_artifacts.py` — 15 new tests (created)
- 223 files untracked via `git rm --cached` (91 state.yaml + 132 stories/*.md)

## Verification
- `git ls-files -- 'apps/*/directions/*/state.yaml' | wc -l` → 0
- `git ls-files -- 'apps/*/stories/*.md' | wc -l` → 0
- `find apps -path '*/directions/*/state.yaml' -type f | wc -l` → 91 (written on disk)
- `find apps -path '*/stories/*.md' -type f | wc -l` → 132 (written on disk)
- `uv run pytest tests/test_gitignore_artifacts.py -q` → 15 passed
- `uv run pytest -q` → full suite green (2225 passed, 3 skipped)

# Senior Developer Review

## Review Status
Pending

## Review Checklist
- [ ] Ignore rules match only machine-written targets
- [ ] Human-authored direction source remains tracked
- [ ] Existing tracked copies removed from index without deleting on-disk files
- [ ] Repo behavior after tick is consistent with story ACs
- [ ] No regeneration/backfill/test-only scope leaked into this story unnecessarily

# Review Follow-ups

- None yet.