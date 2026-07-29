# Story

## Title
Add a factory version command printing the running git SHA and branch — broad read

## Slug
`add-a-factory-version-command-printing-the-running-git-sha-a`

## Scope
`backend`

## Summary
Add a new `factory version` CLI command backed by a pure git-inspection helper that reports the current repo short SHA, branch name, and dirty state. Keep behavior read-only and cover the helper with a temp-repo unit test that asserts reported values match actual git state.

# Acceptance Criteria

- [ ] A new `factory version` CLI command prints the factory repo's current git commit SHA (short) and branch name to stdout.
- [ ] It also indicates whether the working tree is dirty (has uncommitted changes).
- [ ] The command is read-only (no writes, no network) and exits 0 in a valid git repo.
- [ ] A unit test invokes the underlying pure helper against a temp git repo and asserts the reported SHA/branch/dirty flag match the repo state.

### Testable Claims (EARS)
AC1.1: WHEN the operator runs `factory version` in a valid factory git repo, THE CLI SHALL print the repo's current short git commit SHA to stdout.
AC1.2: WHEN the operator runs `factory version` in a valid factory git repo, THE CLI SHALL print the repo's current branch name to stdout.
AC2.1: WHEN the operator runs `factory version` in a valid factory git repo, THE CLI SHALL indicate whether the working tree is dirty.
AC3.1: WHEN `factory version` runs in a valid git repo, THE command SHALL perform no writes.
AC3.2: WHEN `factory version` runs in a valid git repo, THE command SHALL perform no network access.
AC3.3: WHEN `factory version` runs in a valid git repo, THE command SHALL exit with status 0.
AC4.1: WHEN the unit test invokes the underlying pure helper against a temp git repo, THE test SHALL assert that the reported SHA matches the repo state.
AC4.2: WHEN the unit test invokes the underlying pure helper against a temp git repo, THE test SHALL assert that the reported branch matches the repo state.
AC4.3: WHEN the unit test invokes the underlying pure helper against a temp git repo, THE test SHALL assert that the reported dirty flag matches the repo state.

# Tasks / Subtasks

- [ ] Locate existing CLI command registration and output conventions.
- [ ] Add `factory version` command entrypoint.
- [ ] Implement pure git-inspection helper returning short SHA, branch, and dirty flag.
- [ ] Ensure helper reads repo state without writes or network.
- [ ] Wire command output to helper result on stdout.
- [ ] Return exit code 0 in a valid git repo path.
- [ ] Add unit test creating a temp git repo fixture.
- [ ] In test, create committed state and assert short SHA + branch + clean state.
- [ ] In test, introduce uncommitted change and assert dirty state.
- [ ] Keep test isolated from ambient repo state.
- [ ] Run relevant test target for the CLI/helper module.

# Dev Notes

## Direction acceptance criteria (verbatim)

- [ ] A new `factory version` CLI command prints the factory repo's current git commit SHA (short) and branch name to stdout.
- [ ] It also indicates whether the working tree is dirty (has uncommitted changes).
- [ ] The command is read-only (no writes, no network) and exits 0 in a valid git repo.
- [ ] A unit test invokes the underlying pure helper against a temp git repo and asserts the reported SHA/branch/dirty flag match the repo state.

## flow.md

(none)

## api_spec.md

(none)

## Context pointers

No canonical context files were provided in this invocation. Derive implementation entrypoints from the existing CLI codebase and preserve project conventions in-place.

## Implementation constraints

- Back the CLI command with a pure helper so the temp-repo unit test can exercise git-state detection directly.
- Report the current repo state that the running checkout reflects; do not infer from remote state.
- Use short commit SHA, branch name, and dirty-state reporting exactly as required by the direction.
- Preserve read-only behavior: no file writes, no repo mutation, no fetch/pull/network calls.
- Keep stdout output operator-oriented and deterministic enough for assertion at unit/integration boundaries.
- Broad-read interpretation: include all operator-visible dirty-state reporting needed to answer “what code is live right now?” while staying within the stated ACs.

# References

- `Direction`: `D010 factory version command for git SHA, branch, dirty`
- PM child story: `D010 add factory version CLI with git state helper and test`

# Dev Agent Record

## Implementation Log
- Pending

## Files Touched
- Pending

## Test Evidence
- Pending

# Senior Developer Review

- Pending

# Review Follow-ups

- Pending
