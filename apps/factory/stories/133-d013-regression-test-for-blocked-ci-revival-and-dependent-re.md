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

# Dev Agent Record

## Status
Complete

## Completion Notes
The D013 coverage lives in `tests/test_reconcile_from_github.py`. This pass kept the existing regression shape and tightened assertions so each acceptance criterion is explicit:

- Added/kept merged-path side-effect checks (`merged=True` merge-action row and deploy-queue entry) for revived `blocked_ci_unresolved` stories.
- Kept drift-anomaly checks (`state_drift_reconciled`) with payload assertions on the full-path test.
- Extended the full-path regression to advance the revived blocker from `deploy_pending` to `deployed` through the state-machine path, then assert the dependent remains dispatchable (`story_created`).

`uv run pytest -q tests/test_reconcile_from_github.py` passes green.

### AC coverage map
| AC | Test(s) |
|----|---------|
| AC1.1 (blocked_ci in candidates) | `test_blocked_ci_unresolved_merged_pr_revives_to_deploy_pending`, `test_blocked_ci_unresolved_closed_unmerged_stays_blocked` |
| AC2.1 (MERGED → deploy_pending) | `test_blocked_ci_unresolved_merged_pr_revives_to_deploy_pending`, `test_full_path_block_ci_merge_revive_dependent` |
| AC2.2 (merge-action row merged=True) | `test_blocked_ci_unresolved_merged_pr_revives_to_deploy_pending`, `test_blocked_ci_unresolved_revives_dependents`, `test_full_path_block_ci_merge_revive_dependent` |
| AC2.3 (deploy enqueued) | `test_blocked_ci_unresolved_merged_pr_revives_to_deploy_pending`, `test_blocked_ci_unresolved_revives_dependents`, `test_full_path_block_ci_merge_revive_dependent` |
| AC2.4 (outcome matches normal path) | `test_merged_records_merge_action_and_enqueues_deploy` (normal) vs blocked-ci merged tests (same side effects) |
| AC3.1 (CLOSED-unmerged stays blocked) | `test_blocked_ci_unresolved_closed_unmerged_stays_blocked` |
| AC3.2 (no time-based revival) | `test_blocked_ci_unresolved_closed_unmerged_stays_blocked`, `test_blocked_ci_unresolved_open_pr_is_noop` |
| AC4.1 (dependent revived) | `test_blocked_ci_unresolved_revives_dependents`, `test_full_path_block_ci_merge_revive_dependent` |
| AC4.1 edge (multiple blockers) | `test_blocked_ci_unresolved_does_not_revive_when_other_blocker_still_dead` |
| AC5.1 (state_drift_reconciled) | `test_blocked_ci_unresolved_merged_pr_revives_to_deploy_pending`, `test_full_path_block_ci_merge_revive_dependent` |
| AC6.1 (full path deploy_pending) | `test_full_path_block_ci_merge_revive_dependent` |
| AC6.2 (full path dependent unblocked) | `test_full_path_block_ci_merge_revive_dependent` |

## Files Touched
- `tests/test_reconcile_from_github.py` — added deploy progression assertion in `test_full_path_block_ci_merge_revive_dependent`; retained merged/deploy/anomaly assertions across D013 regression tests.
- `apps/factory/stories/133-d013-regression-test-for-blocked-ci-revival-and-dependent-re.md` — refreshed Dev Agent Record to match current coverage and file changes.

# Senior Developer Review

- Pending

# Review Follow-ups

- None yet