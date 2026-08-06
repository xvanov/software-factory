# state-machine — story lifecycle, rollback, and dependency parking

## Overview

`factory/chain/state_machine.py` defines the canonical lifecycle for a
`StoryRecord` (`state/factory.db.stories`). `advance(story, event, payload) ->
StoryState` is pure: it looks up `(current_state, event)` in the `_TRANSITIONS`
dict and returns the next `StoryState`, raising `IllegalTransitionError` for
any pair not in the table. It never mutates the story or touches the
database — `factory/chain/orchestrator.py` and `factory/chain/handlers.py`
own persistence and side effects (LLM calls, GitHub API calls, git writes).

Two chain variants share one enum, selected by `StoryRecord.chain_kind`
(`"tdd"` default, or `"docs"`):

* **`tdd`** (Loop-4, dev-owns-tests): `sm` → `dev` → `review` → `tech_writer`
  → `docs_enforcer` → `PR_OPEN`. The dev persona writes production code AND
  its own tests in one pass; there is no separate test-design/test-impl
  phase.
* **`docs`**: `docs_sm` → `docs_onboarder` → `docs_enforcer` → `PR_OPEN`.
  Used for documentation-only deliverables (e.g. the `context/` bootstrap);
  skips the red/green test loop entirely.

Both converge at `DOCS_ENFORCER_CHECK` and share the PR/CI/merge/deploy tail.
Beyond the happy path, the module also owns 8 terminal "sink" states that
stop the chain from driving a story further (`BLOCKED_*`, `SUPERSEDED_BY_SIBLING`,
`QUARANTINED_INVALID_STATE`, `CLOSED_BY_OPERATOR`) and a dependency-deferral
cap that turns "wait forever behind a dead foundation" into "park and
surface after 3 stalled ticks 45+ minutes apart".

## Key concepts

### The transition table is the only source of truth

`_TRANSITIONS: dict[tuple[StoryState, str], StoryState]` is read literally by
`advance()` — nothing is inferred. The happy-path edges (`state_machine.py:396-506`):

| From | Event | To |
|---|---|---|
| `STORY_CREATED` | `EVENT_SM_STARTED` | `SM_IN_PROGRESS` |
| `SM_IN_PROGRESS` | `EVENT_SM_DONE` | `SM_DONE` |
| `SM_DONE` | `EVENT_DEV_STARTED` | `DEV_IN_PROGRESS` |
| `DEV_IN_PROGRESS` | `EVENT_DEV_TESTS_GREEN` | `TESTS_GREEN` |
| `DEV_IN_PROGRESS` | `EVENT_DEV_TESTS_RED` | `DEV_RETRY` |
| `DEV_IN_PROGRESS` | `EVENT_DEV_EXHAUSTED` | `BLOCKED_TESTS_NEED_CLARIFICATION` |
| `DEV_RETRY` | `EVENT_DEV_STARTED` | `DEV_IN_PROGRESS` |
| `DEV_RETRY` | `EVENT_DEV_EXHAUSTED` | `BLOCKED_TESTS_NEED_CLARIFICATION` |
| `TESTS_GREEN` | `EVENT_REVIEWER_STARTED` | `REVIEWER_IN_PROGRESS` |
| `REVIEWER_IN_PROGRESS` | `EVENT_REVIEWER_APPROVE` | `REVIEWER_DONE` |
| `REVIEWER_IN_PROGRESS` | `EVENT_REVIEWER_REQUEST_CHANGES` | `REVIEWER_REQUESTED_CHANGES` |
| `REVIEWER_IN_PROGRESS` | `EVENT_REVIEW_NONCONVERGENT` | `BLOCKED_REVIEW_NONCONVERGENT` |
| `REVIEWER_REQUESTED_CHANGES` | `EVENT_DEV_STARTED` | `DEV_IN_PROGRESS` |
| `REVIEWER_DONE` | `EVENT_TECH_WRITER_STARTED` | `TECH_WRITER_IN_PROGRESS` |
| `TECH_WRITER_IN_PROGRESS` | `EVENT_TECH_WRITER_DONE` | `TECH_WRITER_DONE` |
| `TECH_WRITER_IN_PROGRESS` | `EVENT_REVIEWER_REQUEST_CHANGES` | `REVIEWER_REQUESTED_CHANGES` |
| `TECH_WRITER_IN_PROGRESS` | `EVENT_REVIEW_NONCONVERGENT` | `BLOCKED_REVIEW_NONCONVERGENT` |
| `TECH_WRITER_DONE` | `EVENT_DOCS_ENFORCER_CHECK` | `DOCS_ENFORCER_CHECK` |
| `DOCS_ENFORCER_CHECK` | `EVENT_DOCS_ENFORCER_PASS` | `PR_OPEN` |
| `DOCS_ENFORCER_CHECK` | `EVENT_DOCS_ENFORCER_FAIL` | `REVIEWER_REQUESTED_CHANGES` |
| `STORY_CREATED` | `EVENT_DOCS_SM_STARTED` | `DOCS_SM_IN_PROGRESS` |
| `DOCS_SM_IN_PROGRESS` | `EVENT_DOCS_SM_DONE` | `DOCS_SM_DONE` |
| `DOCS_SM_DONE` | `EVENT_DOCS_ONBOARDER_STARTED` | `DOCS_ONBOARDER_IN_PROGRESS` |
| `DOCS_ONBOARDER_IN_PROGRESS` | `EVENT_DOCS_ONBOARDER_DONE` | `DOCS_ONBOARDER_DONE` |
| `DOCS_ONBOARDER_IN_PROGRESS` | `EVENT_DOCS_ONBOARDER_FAILED` | `BLOCKED_TESTS_NEED_CLARIFICATION` |
| `DOCS_ONBOARDER_DONE` | `EVENT_DOCS_ENFORCER_CHECK` | `DOCS_ENFORCER_CHECK` |
| `READY_FOR_MERGE` / `CI_GREEN` / `PR_OPEN` | `EVENT_MERGED` | `DEPLOY_PENDING` |
| `PR_OPEN` / `CI_GREEN` / `READY_FOR_MERGE` | `EVENT_PR_UNMERGEABLE` | `BLOCKED_DEPLOY_FAILED` |
| `DEPLOY_PENDING` | `EVENT_DEPLOY_STARTED` | `DEPLOY_PENDING` (self-loop) |
| `DEPLOY_PENDING` | `EVENT_DEPLOY_SUCCEEDED` | `DEPLOYED` |
| `DEPLOY_PENDING` | `EVENT_DEPLOY_FAILED` | `BLOCKED_DEPLOY_FAILED` |
| `DEPLOY_PENDING` | `EVENT_DEPLOY_SKIPPED` | `DEPLOYED` |

Every budget-metered dispatch state (`STORY_CREATED`, `SM_DONE`, `DEV_RETRY`,
`REVIEWER_REQUESTED_CHANGES`, `TESTS_GREEN`, `REVIEWER_DONE`,
`TECH_WRITER_DONE`, `DOCS_SM_DONE`, `DOCS_ONBOARDER_DONE`) also has an
`EVENT_BUDGET_EXCEEDED` → `BLOCKED_BUDGET_EXCEEDED` edge. `DEPLOY_PENDING` is
deliberately unmetered — a merged story must still be allowed to deploy.

`CI_PENDING`, `CI_GREEN`, `READY_FOR_MERGE` have **no edges into them** in
`_TRANSITIONS`; `factory/chain/auto_merge.py` drives a story through those by
**direct state assignment**, not `advance()`. `is_terminal()` — "no outgoing
transition exists" — is therefore true for `CI_PENDING` even though it is not
actually done; callers that need real terminality (dependency-deadlock
detection, tracker-issue closing) use their own explicit allowlists instead
of `is_terminal()` (see "Dependency-deferral cap" below).

### Rollback / rework states

* **`DEV_RETRY`** — the dev sandbox finished with tests still red.
  `story.dev_retries` is bumped and `current_model_tier` may escalate before
  the next dev dispatch. `factory/chain/orchestrator.py:_DISPATCH` maps
  `DEV_RETRY` back to the `dev` handler. Exhausting retries fires
  `EVENT_DEV_EXHAUSTED` → `BLOCKED_TESTS_NEED_CLARIFICATION`.
* **`REVIEWER_REQUESTED_CHANGES`** — the reviewer rejected the diff (code
  defects or test-quality/slop findings). Loop-4 has no separate test
  author, so this state dispatches straight back to `dev`
  (`orchestrator.py:150`). `story.reviewer_cycles` counts consecutive
  request-changes verdicts; at `handlers.py:_MAX_REVIEW_CYCLES = 3` the
  reviewer fires `EVENT_REVIEW_NONCONVERGENT` instead, landing on the
  terminal `BLOCKED_REVIEW_NONCONVERGENT` sink so a non-converging
  dev↔reviewer ping-pong cannot loop unbounded. Two early exits fire
  strictly below that hard cap: identical findings repeating
  `_MAX_REVIEW_STUCK = 2` times (stability guard), and a review score that
  does not IMPROVE between consecutive rejecting cycles (non-improving-score
  guard, 2026-08-01) — flat trajectories buy expensive wrong answers, so
  they block instead of cycling to the cap. Both route only to the blocked
  sink, never to approve.
* **Fail-closed reviewer diff precondition (2026-08-01)** — before any
  reviewer model call, `handlers._fetch_pr_diff_for_review` must yield a real
  diff (`gh pr diff` for PRs; `git diff <base>...HEAD` in the worktree
  otherwise, with an `origin/<base>` → local `<base>` fallback). A fetch
  FAILURE raises and routes the story straight to
  `BLOCKED_REVIEW_NONCONVERGENT` via `EVENT_REVIEW_NONCONVERGENT` without
  burning a reviewer cycle (it used to return the error text AS the diff —
  blind reviews). An EMPTY diff never reaches the model either: the handler
  emits a deterministic request_changes ("commit your work") that stays
  bounded by the guards above. `handle_tech_writer` applies the same
  precondition via its `TECH_WRITER_IN_PROGRESS` →
  `BLOCKED_REVIEW_NONCONVERGENT` edge.
* **`TECH_WRITER_IN_PROGRESS` → `REVIEWER_REQUESTED_CHANGES`** — if
  `apply_context_updates` fails (e.g. tech_writer wrote outside
  `CANONICAL_CONTEXT_PATHS`), the story bounces back through the dev-rework
  path rather than sticking mid-write.
* **`DOCS_ENFORCER_CHECK` fail** — `EVENT_DOCS_ENFORCER_FAIL` also routes to
  `REVIEWER_REQUESTED_CHANGES`, reusing the same rework edge for both chains.
* **CI-failure recovery is NOT a `StoryState` transition** — `auto_merge.py`'s
  `_handle_ci_failure` re-dispatches a red PR up to
  `_MAX_CI_FIX_CYCLES = 3` times by resetting the story back into the dev
  loop directly; only when it gives up (cap reached, or the fix reproduces
  an identical failure signature) does it close the PR and set
  `BLOCKED_CI_UNRESOLVED` by direct assignment.
* **Auto-recovery of blocked stories** — `orchestrator._AUTO_RECOVERABLE_STATES`
  maps `BLOCKED_TESTS_NEED_CLARIFICATION` and `BLOCKED_REVIEW_NONCONVERGENT`
  back to `SM_DONE` (re-runs dev→review→merge). `_recover_blocked_stories`
  applies this at most `_MAX_AUTO_RECOVERIES = 2` times per story and only
  when the story's current failure signature (`_story_failure_signature`,
  volatile bits like timestamps/paths/hex ids stripped) differs from the one
  recorded at the prior recovery — an unchanged signature escalates
  immediately instead of burning another cycle. `BLOCKED_DEPLOY_FAILED` is
  excluded on purpose; that's handled by `auto_merge._attempt_pr_reconcile`.

### Dual-draft sibling supersession

`factory/chain/dual_draft.py` implements the ambiguous-direction flow
(`should_spawn_dual_draft`: PM `confidence < 0.6` or an `(explore)` tag).
Two `StoryRecord`s are spawned per direction, slugs suffixed `-alt-a` /
`-alt-b`. Each runs the normal chain independently and opens its own
`draft-alternative` PR. `close_abandoned_draft_sibling` runs when one
sibling's PR merges (the "winner"):

1. Closes the loser's open PR (`gh pr close --delete-branch`) so it can
   never auto-merge.
2. Closes the loser's tracker issue with `state_reason="not_planned"`
   (best-effort, needs a GitHub client).
3. Sets the loser's `StoryRecord.state` to `SUPERSEDED_BY_SIBLING`
   **by direct assignment**, not via `advance()` — a supersede can fire
   from any in-flight state, so there is no single `EVENT_*` edge that
   fits. This is a pure local DB write and runs even without a GitHub
   client (`github_client is None` only skips the issue-close).

`SUPERSEDED_BY_SIBLING` is terminal (no outgoing transition), excluded from
`auto_merge._MERGEABLE_STATES`, and excluded from concurrency-cap counting.
A sibling already in any terminal state, or at `DEPLOY_PENDING` (the
transient both-merged race), is skipped — a legitimately shipped sibling is
never downgraded. Before this existed, a loser still mid-dev/review could
open its own PR later and ship a second interpretation to main (direction
007 landed both PR #67 and #69).

### Terminal sinks

Nine states have no outgoing transition (`is_terminal()` returns True) and
are absent from `_DISPATCH` and `auto_merge._MERGEABLE_STATES`:

| State | Set by | Recovery |
|---|---|---|
| `DEPLOYED` | `EVENT_DEPLOY_SUCCEEDED` / `EVENT_DEPLOY_SKIPPED` | n/a — success |
| `BLOCKED_TESTS_NEED_CLARIFICATION` | dev/docs-onboarder exhaustion | auto-recovered to `SM_DONE` (capped) or human |
| `BLOCKED_DEPLOY_FAILED` | `EVENT_DEPLOY_FAILED` / `EVENT_PR_UNMERGEABLE` | `auto_merge._attempt_pr_reconcile`, or human |
| `BLOCKED_REVIEW_NONCONVERGENT` | `EVENT_REVIEW_NONCONVERGENT` (stuck/non-improving/capped review cycles, empty-diff short-circuit, or an unfetchable diff at review/tech_writer time) | auto-recovered to `SM_DONE` (capped) or human |
| `BLOCKED_BUDGET_EXCEEDED` | `EVENT_BUDGET_EXCEEDED` | manual: reset state AND zero `total_attempts`/`total_spend_usd`, or raise `caps.per_story_*` |
| `SUPERSEDED_BY_SIBLING` | `dual_draft.close_abandoned_draft_sibling` (direct assignment) | none — permanent |
| `BLOCKED_CI_UNRESOLVED` | `auto_merge._handle_ci_failure` giving up (direct assignment) | operator re-opens PR / re-files direction |
| `BLOCKED_DEPENDENCY_UNMET` | dependency-deadlock OR dependency-deferral cap (see below) | deadlock: manual; cap: automatic once blockers move |
| `QUARANTINED_INVALID_STATE` | `factory.manager.recovery` playbook `quarantine-invalid-enum-story` | manual — operator repairs root cause, clears `error` |
| `CLOSED_BY_OPERATOR` | `orchestrator.reconcile_closed_trackers` (direct assignment) | operator re-opens tracker issue, resets state |

### Dependency ordering and the deferral cap

`orchestrator._direction_deps_pending()` treats story-id order within a
direction as build order (SM emits foundational-first): a story is
dependency-ready only when every lower-id sibling in its direction has
reached `DEPLOYED`. Dual-draft `-alt-a`/`-alt-b` pairs are exempt from each
other (competing interpretations, not a serial dependency).

Two outcomes for a story stuck behind unmet dependencies:

* **Deadlock park** — if every pending dependency sits in
  `_DEAD_END_DEP_STATES` (`SUPERSEDED_BY_SIBLING`, `BLOCKED_CI_UNRESOLVED`,
  `BLOCKED_DEPENDENCY_UNMET`, `CLOSED_BY_OPERATOR` — states that will
  *never* deploy), the dependent is parked in `BLOCKED_DEPENDENCY_UNMET`
  immediately; it can never build.
* **Cap park** — if every pending dependency sits in `_STALLED_DEP_STATES`
  (`_DEAD_END_DEP_STATES` plus the recoverable-pending-human blocks
  `BLOCKED_DEPLOY_FAILED`, `BLOCKED_BUDGET_EXCEEDED`,
  `BLOCKED_TESTS_NEED_CLARIFICATION`, `BLOCKED_REVIEW_NONCONVERGENT`, plus
  `QUARANTINED_INVALID_STATE`) and has been so for at least
  `_MIN_DEP_STALL_SECONDS = 45 * 60` (measured off each blocker's
  `updated_at`), `story.dependency_defer_count` increments. At
  `_MAX_DEPENDENCY_DEFERRALS = 3` consecutive stalled deferrals the
  dependent is parked in `BLOCKED_DEPENDENCY_UNMET` with
  `last_rejection_reason` prefixed `dependency_deferral_cap_exhausted`
  (`state_machine.DEP_DEFER_CAP_REASON_PREFIX`). The counter resets to 0 the
  moment any blocker becomes live again — a story waiting out normal
  dev/review/merge work never accumulates a count no matter how long it
  takes.

`state_machine.is_dependency_cap_parked(state, last_rejection_reason)` is the
single predicate distinguishing a cap-park (revivable) from a deadlock-park
(abandoned) — used by `factory inbox`, the tracker-issue sweep, and the
closed-tracker reconciler so they never disagree.

Cap-parked rows self-heal: `orchestrator._revive_capped_dependents()` scans
`BLOCKED_DEPENDENCY_UNMET` rows carrying the cap marker each tick and, once
no pending dependency is stalled or dead, resumes the story at the state it
was parked *from* (read from the `dependency_deferral_capped` event via
`_dep_cap_resume_state`, falling back to `STORY_CREATED` if that state is no
longer dispatchable) — not from scratch, so a story capped out of
`REVIEWER_DONE` doesn't re-burn SM+dev+review spend. Deadlock-parked rows
have no automatic revival; an operator must move the row back to a live
dispatch state by hand.

## Key files

* `factory/chain/state_machine.py` — `StoryState`, `StoryRecord`, the event
  constants, `_TRANSITIONS`, `advance()`, `is_terminal()`,
  `DEP_DEFER_CAP_REASON_PREFIX`, `is_dependency_cap_parked()`.
* `factory/chain/orchestrator.py` — `_DISPATCH` (state → handler name),
  `_dispatch_for_story()` (adds the `chain_kind` branch out of
  `STORY_CREATED`), `_STATE_PROGRESS_ORDINAL` / `_apply_advance_decay`
  (per-story spend-breaker decay), `_NON_CAP_COUNTING_STATES` /
  `_DOCS_ACTIVE_STATES` (concurrency-cap and docs-serialization exclusions),
  `_DEAD_END_DEP_STATES` / `_STALLED_DEP_STATES` / `_MAX_DEPENDENCY_DEFERRALS`
  / `_MIN_DEP_STALL_SECONDS` (the dependency-deferral cap),
  `_AUTO_RECOVERABLE_STATES` / `_recover_blocked_stories` (blocked-state
  auto-recovery), `reconcile_closed_trackers` (sets `CLOSED_BY_OPERATOR`).
* `factory/chain/rollback.py` — a separate post-merge safety net, NOT part
  of the `StoryState` machine: `rollback_watch_tick()` reads recent rows
  from `merge_actions` (written by `auto_merge.py`), checks main-branch CI
  for each recent merge, and on red opens a revert PR (`gh pr revert`),
  files a `priority/p0` regression issue, and flips the factory mode to
  `fix-only` via `factory.settings.modes.set_mode`. Every decision is
  recorded in `state/factory.db.rollback_actions`
  (`RollbackActionRecord`: `action_type` is `"revert"` or `"no_op"`).
* `factory/chain/dual_draft.py` — `should_spawn_dual_draft`,
  `produce_interpretations`, `link_alternatives` (idempotent tracker
  comment via `LINK_ALTERNATIVES_SENTINEL`), `close_abandoned_draft_sibling`
  (the `SUPERSEDED_BY_SIBLING` supersede logic).
* `factory/chain/handlers.py` — the side-effect layer: each handler (`sm`,
  `dev`, `review`, `tech_writer`, `docs_sm`, `docs_onboarder`,
  `docs_enforcer`, `deploy`) consumes `advance()`'s next-state and persists
  it. Owns `_MAX_REVIEW_CYCLES = 6`.
* `factory/chain/auto_merge.py` — drives `PR_OPEN` → `CI_PENDING` →
  `CI_GREEN` → `READY_FOR_MERGE` → (`EVENT_MERGED`) by direct state
  assignment (these transitions are not in `_TRANSITIONS`); owns
  `_MERGEABLE_STATES`, `_MAX_CI_FIX_CYCLES = 3`, `_handle_ci_failure`, and
  the `BLOCKED_CI_UNRESOLVED` / `BLOCKED_DEPLOY_FAILED` sink assignments.
* `factory/chain/event_log.py` — `log_story_event()` /
  `read_story_events()`. Append-only JSONL at
  `state/logs/<story_id:04d>-<slug>.log`, one file per story so `factory why`
  is a direct file read rather than a scan. Best-effort: every write is
  wrapped so a logging failure (missing dir, permission glitch) can never
  crash a handler or a tick. Event payloads with non-JSON-serializable
  values are stored via `repr()` instead of raising.

## Failure modes

* **`CI_PENDING`/`CI_GREEN` false-terminal via `is_terminal()`.** These
  states have no `_TRANSITIONS` edges (they're driven by `auto_merge.py`
  directly), so a naive `is_terminal(CI_PENDING)` reports `True` even
  though the story is actively mid-merge. Any new caller that needs real
  terminality must use the explicit allowlists (`_DEAD_END_DEP_STATES`,
  `tracker_issue._RESOLVED_STORY_STATES`) instead of `is_terminal()`.
* **Dev↔reviewer non-convergence.** Capped at `_MAX_REVIEW_CYCLES = 3`
  cycles → `BLOCKED_REVIEW_NONCONVERGENT`; auto-recovered to `SM_DONE` at
  most `_MAX_AUTO_RECOVERIES = 2` times, gated on the failure signature
  actually changing between recoveries.
* **CI-fix hamster-wheel.** Before `BLOCKED_CI_UNRESOLVED` existed, a red
  PR that a dev sandbox couldn't fix (pre-existing lint error in an
  unowned file, product-level smoke conflict) sat in `PR_OPEN` forever,
  re-evaluated and re-failing the merge gate every tick (~30 min of git
  work per tick for the same "blocked" conclusion). Now capped at
  `_MAX_CI_FIX_CYCLES = 3` re-dispatches (or an identical failure
  signature) before the PR is closed and the story parked.
* **Dependency deadlock behind a dead foundation.** Before
  `BLOCKED_DEPENDENCY_UNMET` existed, a dependent whose foundation landed
  in a never-to-deploy sink sat in its pre-build state (e.g.
  `STORY_CREATED`) forever — never dispatched (no spend wheel) but never
  resolved, so its direction never completed and its tracker issue never
  closed. Observed 2026-07-23: 6 dual-draft `-alt-b` siblings stranded
  behind `-alt-b`'s abandoned `-alt-a` pair.
* **Dependency deferral without a cap.** `BLOCKED_DEPLOY_FAILED` is
  deliberately not a dead end (an FMS playbook really does revive it), so
  before the cap existed, a dependent behind one deferred every tick
  forever with nothing surfaced to an operator (2026-07-28 deadlock).
  Deferring is correct; deferring unboundedly is the bug the cap closes.
* **Double-merge from an un-retired dual-draft loser.** Before
  `close_abandoned_draft_sibling` closed the loser's PR and superseded its
  `StoryRecord`, only the loser's GitHub issue was closed — a loser already
  holding an auto-merge-enabled PR still merged minutes later, shipping
  both interpretations (direction 007: PR #67 AND #69 both landed).
* **Poisoned rows outside the enum.** A `StoryRecord.state` string set
  outside `StoryState` (a bad manual/manager write, e.g. an `abandoned` row
  that halted the factory for days on 2026-07-07) is skipped by the
  orchestrator's poisoned-row guard every tick — silently and permanently,
  until `factory.manager.recovery`'s `quarantine-invalid-enum-story`
  playbook moves it to `QUARANTINED_INVALID_STATE`, preserving the
  original invalid string in `story.error`.
* **Operator-tracker/local-state disagreement.** A human closing a
  story's tracker issue while the local row still sits in a
  recoverable-pending-human block used to have no representation — the
  factory kept listing the story as awaiting a human days after the human
  had already ruled (observed 2026-07-24: stories 81 and 130, tracker
  issues #267/#337). `reconcile_closed_trackers` now sets
  `CLOSED_BY_OPERATOR` at the top of every tick to close that gap.
* **Rollback is post-merge only, not a `StoryState` concept.** A regression
  that lands on main flips factory mode to `fix-only` and opens a revert
  PR, but the merged story's own `StoryRecord` stays at whatever state it
  reached (typically `DEPLOYED`) — the rollback is tracked in
  `rollback_actions`, not in the chain's state machine.

## Escalation paths

* **Dispatch-time policy rejection** — the orchestrator's cap/mode checks
  (`can_dispatch()`) reject a handler call without any state transition;
  `StoryRecord.last_rejection_reason` records why and the story shows up in
  `factory inbox`. No state change means no event either — the story is
  simply not chosen this tick.
* **Blocked sinks awaiting a human** — `BLOCKED_TESTS_NEED_CLARIFICATION`,
  `BLOCKED_DEPLOY_FAILED`, `BLOCKED_REVIEW_NONCONVERGENT`,
  `BLOCKED_BUDGET_EXCEEDED` are the four states `orchestrator._PENDING_HUMAN_STATES`
  tracks as revivable-by-operator; `factory inbox` surfaces them.
  `BLOCKED_TESTS_NEED_CLARIFICATION` and `BLOCKED_REVIEW_NONCONVERGENT` also
  get automatic bounded re-attempts via `_AUTO_RECOVERABLE_STATES` before a
  human needs to act.
* **Permanent sinks** — `SUPERSEDED_BY_SIBLING`, `BLOCKED_CI_UNRESOLVED`,
  `BLOCKED_DEPENDENCY_UNMET` (deadlock variant), `QUARANTINED_INVALID_STATE`,
  `CLOSED_BY_OPERATOR` all resolve their tracker issue automatically
  (`tracker_issue._RESOLVED_STORY_STATES`) and are surfaced to the FMS
  (`factory_improver._terminally_blocked_stories`) rather than to the
  interactive operator inbox — there is nothing actionable left except a
  manual state reset for the rare case an operator wants to retry.
* **Rollback escalation** — `rollback_watch_tick()` files a
  `priority/p0` GitHub issue with the merged PR link, the suspect commit,
  and the failing test names, then calls `set_mode("fix-only", ...)` so
  feature work pauses factory-wide until the regression is addressed.
  This is the one escalation path that changes factory *mode* rather than
  any single story's state.
* **`factory why <id>` / `factory trace <id>`** — read
  `state/logs/<story_id>-<slug>.log` via `event_log.read_story_events()`.
  This is the audit trail of *how* a story reached its current state and
  *why* a transition happened (handler start/end, `dev_retry`,
  `dev_exhausted`, `dependency_deferral_capped`, `dependency_defer_revived`,
  `auto_recovery`, `handler_exception`, etc.) — the chain's own state only
  tells you *what* state a story is in now.
