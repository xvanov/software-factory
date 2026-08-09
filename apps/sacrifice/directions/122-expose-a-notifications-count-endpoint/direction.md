---
title: Expose a total notification count for the authenticated user
type: feature
priority: p2
explore: false
created_at: '2026-08-09T12:00:00+00:00'
related_directions: []
---

# Expose a total notification count for the authenticated user

## Why

`GET /api/notifications/unread-count` exists
(`backend/app/routes/notifications.py:44-50`) but there is no way to learn a
caller's *total* notification count without paging the full list via
`GET /api/notifications` (`notifications.py:32-39`, capped at 100 per page).
A caller who wants to show "47 notifications" without deciding a page size, or
who wants to detect that a notification was created at all (independent of
read/unread state), has to page and count client-side. A dedicated total count
is the same shape as the existing unread count, one query away.

This direction exercises Workstream D's second shape on purpose: the criterion
that matters is not "does the endpoint answer" but "does it correctly reflect
an entity created moments earlier by the same caller" — the setup-vs-assert
split (Workstream A3) and the shared-DB per-caller-scoping discipline
(Workstream A1's KNOWN OPEN #2, see below) both get exercised here in a way
D-1's stateless read cannot.

## Why `explore: false`

Same reasoning as D-1: `explore: true` makes SM emit two competing full
alternates for the same criteria, and `superseded_by_sibling` on the loser is
the *normal* outcome (23/23 deployed, 20/23 superseded, measured 2026-08-08/09)
— not a build failure, but noise this unattended proof cannot afford to
misread as one. `explore: false` gives one SM decomposition, one oracle graded
against this direction's own `acceptance` list, no sibling to be superseded by.
The `explore` question itself is Workstream A4's decision, already made
elsewhere — not re-opened here.

## Acceptance Criteria

- [ ] Immediately after registering a new account (no goals, no notifications
  yet created for that account), `GET /api/notifications/count` returns `200`
  with body `{"count": 0}` for that caller.
- [ ] After that same caller creates exactly one goal via `POST /api/goals`,
  `GET /api/notifications/count` for that caller returns `200` with body
  `{"count": 1}` — reflecting the single automatic `goal_created` notification
  that goal creation already fires
  (`backend/app/routes/goals.py:139-146`, verified: this is existing behavior,
  not new in this direction).
- [ ] An unauthenticated `GET /api/notifications/count` is rejected rather than
  returning any count (assert status `401` only — see the operator-ratified
  rule below on error-path bodies this direction did not introduce).

## Out of scope

- Filtering by notification type or read/unread state. `unread-count` already
  covers unread; this is the unfiltered total, nothing more.
- Any change to `GET /api/notifications` (list) or `GET
  /api/notifications/unread-count`. Both keep their current contracts.
- Any change to what creates a notification. Goal creation already creates
  exactly one `goal_created` notification (`goals.py:139-146`); this direction
  reads that count, it does not add, remove, or alter any notification-creation
  call site (there are five others across the app — `goals.py:360`, `:369`,
  `:584`, `verification_result.py`, `blocked_goals.py`, `chat.py`,
  `direction_synth.py` — none of them fire on a plain `POST /api/goals`, and
  none should be touched by this story).

## The 401 body — do not assert its wording

`GET /api/notifications/count` reuses `get_current_user`
(`backend/app/core/dependencies.py`), the same dependency every other
authenticated route uses. Direction 120's oracle asserted a specific `401` body
wording it invented, the app's real dependency has raised different wording
since before that direction existed, and the resulting false block was
corrected in operator ratification (`apps/sacrifice/directions/120-…/api_spec.md`,
"Operator ratification — 2026-08-09"; the `contract` persona's rule 2d and
`acceptance_author` persona, factory PR #277). Assert the **status code only**
for this criterion. This direction does not introduce `get_current_user` or its
error body, so it has no standing to assert what that body says.

## Prerequisite-state mechanics — read before writing the oracle setup

`POST /api/goals` runs its criteria gate (`gate_criteria`,
`backend/app/services/goal.py:132`) **unconditionally**, even for a `draft`-
status goal (the default; `GoalCreate` has no `status` field, so every
`POST /api/goals` creates a `draft` goal —
`backend/app/schemas/goal.py:11-21`). A verified, minimal valid body for this
story's setup step:

```json
{
  "title": "<ACCEPTANCE_RUN_ID>-notif-count-check",
  "deadline": "<now + 7 days, ISO-8601>",
  "pledge_amount": 500,
  "goal_type": "api_endpoint",
  "criteria": {
    "url": "https://example.com/health",
    "method": "GET",
    "expected_status": 200
  }
}
```

`api_endpoint`'s criteria schema requires exactly `url`, `method`,
`expected_status` (`backend/app/goal_types/api_endpoint/definition.py`,
`criteria_schema.required`); `expected_status` must be an integer in
`[100, 599]`. The deadline only needs to clear
`DEADLINE_MIN_LEAD` (1 hour, `backend/app/services/input_parsing.py:20`) — and
only for `active`/`pending_review` status, which a `draft` goal never reaches
in this story — so 7 days out is comfortably safe and requires no activation
step. **This story never activates the goal, never submits proof, and never
touches the verification pipeline** — it only needs the `POST /api/goals` call
to return `201`, which fires the notification this story observes.

## Shared-database contamination — required reading before trusting a red

`acceptance_boot.env` points at the **shared** dev Postgres
(`apps/sacrifice/config.yaml`, and its own comment says so). This is precisely
the shape Workstream A's KNOWN OPEN #2 describes
(`factory/chain/gates/acceptance_verified.py`, module docstring, item 2):

- **Namespace every created entity with `ACCEPTANCE_RUN_ID`.** Use it (or a
  value derived from it) in the registered account's email local-part and in
  the created goal's `title`, so this run's rows are attributable and cannot be
  read as another run's leftovers.
- As of the module docstring dated 2026-08-09, `_evaluate` now appends a
  per-evaluation nonce, so `ACCEPTANCE_RUN_ID` is genuinely unique per HEAD and
  BASE run — the worst-case collision (a deterministic run id colliding with
  its *own* prior evaluation, observed on story 179) is closed. Two residuals
  remain per that docstring: (a) the ablation route
  (`_ablation_can_fail`) still reuses one run id across its baseline and every
  mutant — not expected to fire here, since the mutation-testing ablation gate
  is dormant and has never been flipped on in this repo (memory:
  `ablation_gate_dormant_and_broken`) — and (b) an oracle that hardcodes an
  identifier instead of using `ACCEPTANCE_RUN_ID` still collides regardless of
  the nonce. This direction's setup **must** use `ACCEPTANCE_RUN_ID`, not a
  literal string, for exactly that reason.
- **Every acceptance criterion above is scoped to the account this story's own
  setup creates** — never a global count or list. `{"count": 0}` and
  `{"count": 1}` are asserted for *that specific caller's* token, not for "the
  count" in any absolute sense. A shared Postgres has other rows in it from
  other runs and other stories; a global assertion would be false by
  construction the moment two stories run concurrently.
- **A red on this story is not believed on first sight.** Before treating a
  failure here as a real defect: confirm it is not a duplicate-identifier
  `409`/`422` from a leftover row (registration email collision, most likely) —
  read `state/acceptance/sacrifice/<story-id>/*.json` (`stub_runs.json`,
  `base_runs.json`, and `run_ids.json` if present) for the actual request/response
  pair before concluding anything — and re-run the gate once before treating a
  repeat failure as evidence. This is a process requirement for evaluating this
  specific story's result, not an escape hatch for a genuinely broken
  implementation.

## Expected size (pre-registered, for the benchmark record)

One vertical slice, one story:

- New files: 1 (a test file, e.g. `backend/tests/test_notification_count.py`).
- Modified files: 1 (`backend/app/routes/notifications.py`, adding one `GET
  /count` route to the existing router — no shadow-routing hazard here: this
  router has no `GET /{notification_id}`-shaped catch-all, only `PUT
  /{notification_id}/read`, a different HTTP method, so ordering is not a
  concern the way it is in `goals.py`).
- Estimated sandbox iterations: same order of magnitude as 119/120 (60-90) —
  one query, one new route, one dependency already in use elsewhere in the same
  file's neighborhood (`get_unread_count` in
  `backend/app/services/notification.py:82` is the pattern to copy).

Well inside the PM per-story caps and the A4 collapse thresholds; no split
expected.
