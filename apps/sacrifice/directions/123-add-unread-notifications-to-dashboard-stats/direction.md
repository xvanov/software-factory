---
title: Add an unread-notification count to the dashboard stats response
type: feature
priority: p2
explore: false
created_at: '2026-08-09T12:00:00+00:00'
related_directions: []
---

# Add an unread-notification count to the dashboard stats response

## Why

`GET /api/dashboard/stats` (`backend/app/routes/dashboard.py:14-72`) already
aggregates everything the dashboard's summary strip needs — goal counts,
success rate, pledged/saved/donated totals — in one call. Unread notification
count is a second number a dashboard summary strip commonly wants (a badge),
and today getting it costs a second round trip to
`GET /api/notifications/unread-count`
(`backend/app/routes/notifications.py:44-50`). Folding it into the existing
stats payload removes that second call for any client that already fetches
stats on page load.

This is Workstream D's third shape on purpose: a change to an **existing**,
already-shipped endpoint, chosen specifically to be additive-only (a new field
on an existing response) rather than a change to existing behavior, and chosen
after measuring its blast radius (below) rather than assuming it. Direction 117
picked an existing-endpoint change (`POST /api/goals`) without measuring first,
broke ~40 sibling tests, exhausted two `explore` alternates and 6 dev attempts,
and burned ~$14 before terminating unbuilt as stories 177/178 (memory:
`direction_117_was_oversized_for_one_story`). This direction exists to avoid
repeating that.

## Why `explore: false`

Same reasoning as D-1 and D-2: `explore: true` makes SM emit two competing full
alternates for the same criteria and `superseded_by_sibling` on the loser is
the *normal*, correct outcome (23/23 deployed, 20/23 superseded, measured
2026-08-08/09) — not a build failure, but noise this unattended, three-story
proof cannot afford to have misread as one. `explore: false` gives one SM
decomposition, one oracle graded against this direction's own `acceptance`
list. The `explore` question itself is Workstream A4's decision, made
elsewhere, not re-opened here.

## Blast radius — measured, not assumed (pre-registered before filing)

Before choosing `GET /api/dashboard/stats`, the following candidates were
checked with `grep -rl "<route>" backend/tests/` (run from
`/home/k/sacrifice/backend/tests/`, 2026-08-09):

| candidate route | files referencing it |
|---|---|
| `/api/goals` (bare, any method) | **28** — excluded, far over budget |
| `/api/health` | 5 — excluded |
| `/api/auth/me` | 4 — excluded |
| `/api/goals/count` | 1 (`test_goal_count.py`) — in-flight direction 120 territory, excluded to avoid colliding with another story touching the same route while it may still be unmerged |
| `/api/dashboard/stats` | **1** (`test_dashboard.py`) — **selected** |
| `/api/dashboard/history` | 1 (`test_dashboard.py`) — same file, not selected (see below) |
| `/api/notifications/unread-count` | 1 (`test_notifications.py` — not touched by this direction) |
| `/api/payment/config` | 1 (`test_payment.py`) — not selected, lower value |
| `/api/goal-types` | 1 (`test_goals.py`) — not selected, lower value |

**Selected: `GET /api/dashboard/stats`, referenced in exactly 1 test file
(`backend/tests/test_dashboard.py`), pre-registered at 1.** The ≤3-file bound
from the plan is met with margin. `/api/dashboard/history` shares the same test
file but is a different route on the same router and is out of scope (see
below) — not touched, so it does not add to the count.

## Acceptance Criteria

- [ ] Immediately after registering a new account (no goals, no notifications
  yet for that account), `GET /api/dashboard/stats` returns `200` with a new
  `unread_notifications` field equal to `0`, alongside the existing response
  fields (`total_goals`, `completed_count`, `failed_count`, `success_rate`,
  `total_pledged`, `total_donated`, `total_saved` —
  `backend/app/routes/dashboard.py:64-71` — all unchanged in shape and
  computation).
- [ ] After that same caller creates one goal via `POST /api/goals`,
  `GET /api/dashboard/stats`'s `unread_notifications` field equals `1` (the
  automatic `goal_created` notification, unread by default —
  `backend/app/models/notification.py:34`, `read: Mapped[bool] =
  mapped_column(Boolean, default=False)`) **while** `total_goals` in the same
  response also equals `1` — confirming the new field did not disturb the
  existing ones it sits beside.
- [ ] `unread_notifications` in `GET /api/dashboard/stats` exactly matches the
  value simultaneously obtainable from the existing, unmodified
  `GET /api/notifications/unread-count` for the same caller — asserting the new
  field is a read of the same source of truth
  (`get_unread_count`, `backend/app/services/notification.py:82`), not a second,
  independently-computed count that can drift from it.

## Out of scope

- `GET /api/dashboard/history` (`dashboard.py:75-98`). Same file, same router,
  not touched — keeping the diff to one route in one file is what keeps the
  blast radius at 1 test file rather than whatever `history` alone would add.
- Any change to `GET /api/notifications/unread-count` itself. It stays exactly
  as it is; this direction only reads the same underlying count from a second
  place.
- Marking anything read. This is a read-only aggregation; no notification's
  `read` state changes as a side effect of calling `/api/dashboard/stats`.
- Any other field on `/api/dashboard/stats`'s response. `total_goals`,
  `completed_count`, `failed_count`, `success_rate`, `total_pledged`,
  `total_donated`, `total_saved` all keep their current values and
  computations unchanged — this is additive, one new field, nothing removed or
  recomputed.

## Does a `blocked_budget_exceeded` outcome falsify this benchmark run?

**Explicit call, made in advance per the plan's instruction not to decide this
after seeing the result: no, it does not falsify the plan.** A budget block on
this specific, measured-blast-radius, additive-only story would be a **finding
about the harness** (the retry/cost accounting Workstream E describes, or an
oracle false-block burning dev attempts) — pre-registered here as a possible
but unexpected outcome, not evidence that Workstream D's proof concept is
wrong. It should be logged, diagnosed, and reported honestly (per the plan's
"Reporting" section) rather than silently retried or waived. Contrast with
direction 117: that block was plausibly explained by an unmeasured blast radius
(~40 sibling tests) — this direction exists specifically to remove that
variable by measuring first, so a budget block here would be *more*
informative, not less, about a different failure mode (harness retry cost, not
scope misjudgment).

## Expected size (pre-registered, for the benchmark record)

One vertical slice, one story:

- New files: 0.
- Modified files: 2 (`backend/app/routes/dashboard.py`, adding one field to one
  handler's return dict — no `response_model` to update, since this endpoint
  returns a plain `dict`, not a Pydantic schema, per
  `backend/app/routes/dashboard.py:14-15`; and `backend/tests/test_dashboard.py`,
  extending the existing stats test rather than adding a new file).
- Estimated sandbox iterations: smaller than 119/120 (60-90) — this is a
  one-line addition to an existing, already-tested handler reusing an
  already-imported pattern (`get_unread_count` is already imported and used in
  `backend/app/routes/notifications.py`; import it into `dashboard.py` the same
  way). Expect well under 60.

This is the smallest of the three D directions by file count, which is
deliberate: D-3 is the shape direction 117 showed can balloon, so this one is
sized to make ballooning implausible rather than merely hoped against.
