# Story

## Title
Add a factory version command printing the running git SHA and branch — narrow read

## Slug
`add-a-factory-version-command-printing-the-running-git-sha-a`

## Scope
`backend`

## Summary
Add a new `factory version` CLI command backed by a pure git-state helper that reports the current short commit SHA, branch name, and dirty state for the factory repo. Keep the implementation read-only and cover the helper with a temp-repo unit test that proves reported SHA/branch/dirty values match actual repo state.

# Acceptance Criteria

- [ ] A new `factory version` CLI command prints the factory repo's current git commit SHA (short) and branch name to stdout.
- [ ] It also indicates whether the working tree is dirty (has uncommitted changes).
- [ ] The command is read-only (no writes, no network) and exits 0 in a valid git repo.
- [ ] A unit test invokes the underlying pure helper against a temp git repo and asserts the reported SHA/branch/dirty flag match the repo state.

### Testable Claims (EARS)
AC1.1: WHEN `factory version` is invoked in a valid git repo, THE CLI SHALL print the factory repo's current git commit SHA (short) to stdout.
AC1.2: WHEN `factory version` is invoked in a valid git repo, THE CLI SHALL print the factory repo's current branch name to stdout.
AC2.1: WHEN `factory version` is invoked in a valid git repo, THE CLI SHALL indicate whether the working tree is dirty.
AC3.1: WHEN `factory version` is invoked in a valid git repo, THE command SHALL perform no writes.
AC3.2: WHEN `factory version` is invoked in a valid git repo, THE command SHALL perform no network access.
AC3.3: WHEN `factory version` is invoked in a valid git repo, THE command SHALL exit with status 0.
AC4.1: WHEN the unit test invokes the underlying pure helper against a temp git repo, THE test SHALL assert that the reported SHA matches the repo state.
AC4.2: WHEN the unit test invokes the underlying pure helper against a temp git repo, THE test SHALL assert that the reported branch matches the repo state.
AC4.3: WHEN the unit test invokes the underlying pure helper against a temp git repo, THE test SHALL assert that the reported dirty flag matches the repo state.

# Tasks / Subtasks

- [ ] Locate existing CLI command registration and command-handler patterns.
- [ ] Add pure helper for git-state inspection scoped to factory repo path.
- [ ] Return short commit SHA from helper.
- [ ] Return branch name from helper.
- [ ] Return dirty-state flag from helper.
- [ ] Ensure helper is read-only and uses local git metadata only.
- [ ] Wire new `factory version` command into CLI.
- [ ] Print SHA, branch, and dirty-state to stdout.
- [ ] Exit 0 in valid git repo path.
- [ ] Add unit test creating temp git repo fixture.
- [ ] In test, create committed state and assert helper SHA/branch values.
- [ ] In test, introduce uncommitted change and assert dirty flag changes.
- [ ] Keep test focused on helper, not shelling through full CLI unless already idiomatic.

# Dev Notes

## Direction inputs
[flow.md: none]
[api_spec.md: none]

## Context pointers
No canonical context files were provided in this invocation. Derive implementation points from repository code structure during development.

## Acceptance criteria (verbatim embed)
- [ ] A new `factory version` CLI command prints the factory repo's current git commit SHA (short) and branch name to stdout.
- [ ] It also indicates whether the working tree is dirty (has uncommitted changes).
- [ ] The command is read-only (no writes, no network) and exits 0 in a valid git repo.
- [ ] A unit test invokes the underlying pure helper against a temp git repo and asserts the reported SHA/branch/dirty flag match the repo state.

## Implementation boundaries
- Narrow read: implement only the operator-visible `factory version` command plus the minimal pure helper and unit test required by the direction.
- Do not expand into unrelated diagnostics, environment reporting, build metadata, remote git inspection, or docs churn unless directly required to register the command.
- Prefer an output shape that is stable and directly testable for presence of SHA, branch, and dirty indicator without adding extra claims not in the direction.
- Helper must remain pure with respect to caller-visible side effects: inspect repo state, return values, no writes.
- Unit test should validate helper behavior against a temporary local git repository under controlled committed and dirty states.

# References

- Direction: `D010 factory version command for git SHA, branch, dirty`
- PM tracker title: `D010 factory version command for git SHA, branch, dirty`
- PM rationale: one vertical slice covering helper, CLI command, and temp-repo unit test.

# Dev Agent Record

- Status: Not started
- Agent: TBD
- Branch: TBD
- Notes:
  - TBD

# Senior Developer Review

- Status: Pending
- Reviewer: TBD
- Review notes:
  - TBD

# Review Follow-ups

- None yet.
