---
title: Expose a draft goal count for the authenticated user
type: feature
priority: p2
explore: false
created_at: '2026-08-10T12:00:00+00:00'
related_directions: []
---

# Expose a draft goal count for the authenticated user

## Why

`GET /api/goals/count` exists (`backend/app/routes/goal_count.py`, direction
120) and returns the caller's total goal count, and `GET /api/dashboard/stats`
returns aggregate counts by *outcome* (`completed_count`, `failed_count`) —
but nothing exposes how many of a caller's goals are still sitting in `draft`
(created, never activated). A caller building a "finish setting up your goals"
nudge has to page `GET /api/goals` and count client-side. Every `POST
/api/goals` creates a `draft` goal (the default; `GoalCreate` has no `status`
field — `backend/app/schemas/goal.py:11-21`), so a dedicated draft count is
one `WHERE status = 'draft'` away from the existing count query.

This is a fresh Workstream D-2 shape (prerequisite state: create an entity,
then observe it) — the re-proof after the 2026-08-10 abort. The prior D-2
(direction 122, story 185) parked on an ORACLE-AUTHOR defect (an invented
weak password failing every SETUP register call), not on the chain or this
shape. The author-side class fixes (authoring-time collect smoke, the
password-pattern harness fact, the bounded all-SETUP auto-re-author) are
merged; this direction is the fresh, unattended validation of exactly that
class.

## Why `explore: false`

Same reasoning as directions 121-123: `explore: true` makes SM emit two
competing full alternates and `superseded_by_sibling` on the loser is the
normal outcome (23/23 deployed, 20/23 superseded, measured 2026-08-08/09) —
noise this unattended proof cannot afford to misread as a failure.
`explore: false` gives one SM decomposition and one oracle graded against
this direction's own `acceptance` list.

## Acceptance Criteria

- [ ] Immediately after registering a new account (no goals yet created for
  that account), `GET /api/goals/draft-count` returns `200` with body
  `{"count": 0}` for that caller.
- [ ] After that same caller creates exactly one goal via `POST /api/goals`
  (which creates it in `draft` status by default — verified:
  `backend/app/schemas/goal.py:11-21` has no `status` field), `GET
  /api/goals/draft-count` for that caller returns `200` with body
  `{"count": 1}`.
- [ ] An unauthenticated `GET /api/goals/draft-count` is rejected rather than
  returning any count (assert status `401` only — this direction does not
  introduce `get_current_user` and has no standing to assert its error body).

## Out of scope

- Any change to `GET /api/goals/count`, `GET /api/goals` (list), or
  `GET /api/dashboard/stats`. All keep their current contracts.
- Counts for any other status (`active`, `pending_review`, `verified`,
  `failed`). Draft only.
- Activating goals, submitting proof, or anything in the verification
  pipeline. This story only needs `POST /api/goals` to return `201`.

## Blast radius — pre-registered (Workstream D discipline)

`grep -rl "goals/draft-count" backend/tests/` at authoring time: **0 files**
(the route is new). `grep -rl "goal_count" backend/tests/`: **1 file**
(`test_goal_count.py`), which this story does not modify. Pre-registered
bound: ≤3 test files touched. The natural implementation is a sibling route
in `backend/app/routes/goal_count.py` (registered before `goals.py`'s
parameterised `/{goal_id}` route — the same ordering that makes
`GET /api/goals/count` reachable today; keeping the new route in the same
router inherits that ordering for free).

## The 401 body — do not assert its wording

Same operator-ratified rule as directions 120/122: assert the **status code
only** for the unauthenticated criterion. This direction reuses
`get_current_user` and did not introduce its error body.

## Prerequisite-state mechanics — read before writing the oracle setup

A verified, minimal valid body for this story's setup `POST /api/goals` step
(same facts as direction 122, re-verified 2026-08-10):

```json
{
  "title": "<ACCEPTANCE_RUN_ID>-draft-count-check",
  "deadline": "<now + 7 days, ISO-8601, computed at runtime>",
  "pledge_amount": 500,
  "goal_type": "api_endpoint",
  "criteria": {
    "url": "https://example.com/health",
    "method": "GET",
    "expected_status": 200
  }
}
```

The response is `201` and the created goal's status is `draft` — which is the
very state this direction counts. **The arrange step uses only routes that
exist at the merge base** (`/api/auth/email/register`, `/api/goals`) — never
the story's own new route (KNOWN OPEN #5 discipline,
`factory/chain/gates/acceptance_verified.py` module docstring).

## Shared-database contamination — required reading before trusting a red

Same as direction 122: `acceptance_boot.env` points at the shared dev
Postgres. Namespace the registered email's local-part and the created goal's
title with `ACCEPTANCE_RUN_ID`; scope every assertion to this story's own
caller's token, never a global count. The per-evaluation run-id nonce
(2026-08-09) makes run ids genuinely unique; a red should still be checked
against leftover-row shapes (`409` on register) before being believed.
