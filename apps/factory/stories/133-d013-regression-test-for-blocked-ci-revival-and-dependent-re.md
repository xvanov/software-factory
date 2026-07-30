# Story

## Title
D013 regression test for blocked CI revival and dependent release

## Slug
`d013-regression-test-for-blocked-ci-revival-and-dependent-re`

## Scope
`test`

## Summary
Add regression coverage for the blocked-CI recovery path: a story blocked at `blocked_ci_unresolved` is merged out of band, `reconcile_from_github` revives it onto the normal merged path, and a dependent blocked on it becomes dispatchable again after the blocker reaches `deployed`.

# Acceptance Criteria

- `reconcile_from_github` considers stories in `blocked_ci_unresolved` that carry
  a positive `github_pr_number`, in addition to the current mergeable states.
- A story in `blocked_ci_unresolved` whose PR is MERGED on GitHub advances to
  `deploy_pending`, records a `merged=True` merge-action row, and enqueues the
  deploy — the same outcome as the normal reconciled-merge path.
- A story in `blocked_ci_unresolved` whose PR is still CLOSED-unmerged stays
  blocked, so reviving is driven by the real artifact and never by the mere
  passage of time.
- Reviving a story re-evaluates its dependents: a story in
  `blocked_dependency` whose blocker reached `deployed` becomes dispatchable
  again.
- The revival is logged as a `state_drift_reconciled` anomaly, like every other
  reconciliation, so it is never silent.
- A test asserts the full path: block a story on CI, merge its PR out of band,
  run reconcile, and observe `deploy_pending` plus an unblocked dependent.

### Testable Claims (EARS)
AC1.1: WHEN `reconcile_from_github` selects stories to inspect, GIVEN a story is in `blocked_ci_unresolved` and has a positive `github_pr_number`, THE reconciliation logic SHALL include that story in addition to stories in the current mergeable states.
AC2.1: WHEN `reconcile_from_github` observes that a story in `blocked_ci_unresolved` has a PR that is MERGED on GitHub, THE story SHALL advance to `deploy_pending`.
AC2.2: WHEN `reconcile_from_github` revives a story in `blocked_ci_unresolved` from a GitHub MERGED PR, THE system SHALL record a merge-action row with `merged=True`.
AC2.3: WHEN `reconcile_from_github` revives a story in `blocked_ci_unresolved` from a GitHub MERGED PR, THE system SHALL enqueue the deploy.
AC2.4: WHEN `reconcile_from_github` revives a story in `blocked_ci_unresolved` from a GitHub MERGED PR, THE outcome SHALL match the normal reconciled-merge path.
AC3.1: WHEN `reconcile_from_github` observes that a story in `blocked_ci_unresolved` has a PR that is CLOSED-unmerged on GitHub, THE story SHALL remain blocked.
AC3.2: WHEN a story in `blocked_ci_unresolved` has a PR that is CLOSED-unmerged on GitHub, THE system SHALL not revive the story based on the mere passage of time.
AC4.1: WHEN a revived story's blocker reaches `deployed`, GIVEN another story is in `blocked_dependency` because of that blocker, THE dependent story SHALL become dispatchable again.
AC5.1: WHEN `reconcile_from_github` revives a story from drift between factory state and GitHub merged state, THE system SHALL log a `state_drift_reconciled` anomaly.
AC6.1: WHEN the regression test blocks a story on CI, merges its PR out of band, and runs reconcile, THE test SHALL observe the story at `deploy_pending`.
AC6.2: WHEN the regression test advances the blocker to `deployed` after the out-of-band merge and reconcile path, THE test SHALL observe an unblocked dependent.

# Tasks / Subtasks

- [ ] Identify existing reconciliation integration test file covering merged PR handling.
- [ ] Extend fixture/setup to create:
  - [ ] blocker story in `blocked_ci_unresolved`
  - [ ] positive `github_pr_number`
  - [ ] dependent story in `blocked_dependency`
- [ ] Stub/mock GitHub PR lookup for MERGED result.
- [ ] Execute `reconcile_from_github` in test.
- [ ] Assert blocker transitions to `deploy_pending`.
- [ ] Assert merge-action persistence includes `merged=True`.
- [ ] Assert deploy enqueue side effect matches existing merged reconciliation assertions.
- [ ] Assert anomaly log contains `state_drift_reconciled`.
- [ ] Advance blocker to `deployed` using existing test helper/path.
- [ ] Assert dependent becomes dispatchable again.
- [ ] Add negative assertion path for CLOSED-unmerged PR staying `blocked_ci_unresolved` if covered in same file without obscuring the main path.
- [ ] Keep assertions aligned with existing state-machine terminology and helper APIs.

# Dev Notes

## Flow Embed
# Operator flow — recovering a CI-blocked story

1. **Find the blocked story.** The operator runs `factory queue --app factory`
   and sees a story at `blocked_ci_unresolved`, with its dependents at
   `blocked_dependency`.

2. **Read why it gave up.** `factory why <id>` shows the `ci_fix_redispatch`
   attempts and the exhaustion reason (e.g. `identical_failure_signature`), and
   the auto-close comment on the PR says the same.

3. **Fix the branch.** The operator pushes a fix to the story's branch, reopens
   the PR if the factory closed it, and watches CI go green.

4. **Merge it.** The operator squash-merges the PR. The code is now on the
   default branch.

5. **Observe the story revive.** On the next tick the operator sees the story
   move from `blocked_ci_unresolved` to `deploy_pending`, and then `deployed` —
   without hand-editing the database. Today this step never happens.

6. **Observe the dependents release.** The stories that were
   `blocked_dependency` on it become dispatchable, and the direction continues
   on its own.

7. **Confirm nothing revived spuriously.** A different story whose PR was closed
   without merging is still `blocked_ci_unresolved` after the same tick.

## API Spec Embed
(none)

## Context Pointers
No canonical context files were provided in the prelude.

## Direction Acceptance Criteria (verbatim embed)
- `reconcile_from_github` considers stories in `blocked_ci_unresolved` that carry
  a positive `github_pr_number`, in addition to the current mergeable states.
- A story in `blocked_ci_unresolved` whose PR is MERGED on GitHub advances to
  `deploy_pending`, records a `merged=True` merge-action row, and enqueues the
  deploy — the same outcome as the normal reconciled-merge path.
- A story in `blocked_ci_unresolved` whose PR is still CLOSED-unmerged stays
  blocked, so reviving is driven by the real artifact and never by the mere
  passage of time.
- Reviving a story re-evaluates its dependents: a story in
  `blocked_dependency` whose blocker reached `deployed` becomes dispatchable
  again.
- The revival is logged as a `state_drift_reconciled` anomaly, like every other
  reconciliation, so it is never silent.
- A test asserts the full path: block a story on CI, merge its PR out of band,
  run reconcile, and observe `deploy_pending` plus an unblocked dependent.

## Scope Notes
- This is the validation slice after backend reconciliation behavior exists.
- Primary objective: preserve a single readable regression that exercises the operator recovery path end to end.
- Do not expand coverage into other blocked sink states.
- Do not change CI retry-cap behavior.
- Prefer existing integration/e2e helpers over new bespoke fixtures.
- If negative CLOSED-unmerged coverage exists already, update it only as needed to keep blocked behavior explicit.

# References

- Direction: D013 revive blocked_ci_unresolved after merged PR
- PM tracker: `D013 revive blocked_ci_unresolved after merged PR`
- Story dependency context: backend slice `D013 reconcile blocked_ci_unresolved merged PR to deploy_pending`

# Dev Agent Record

## Status
Not started

## Agent Notes
- To be completed by Dev.

## Files Touched
- To be completed by Dev.

# Senior Developer Review

- Pending

# Review Follow-ups

- None yet
