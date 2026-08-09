---
title: Expose the recurrence options a goal can be created with
type: feature
priority: p2
explore: false
created_at: '2026-08-09T12:00:00+00:00'
related_directions: []
---

# Expose the recurrence options a goal can be created with

## Why

`POST /api/goals` and `PUT /api/goals/{id}` both validate `recurrence` against a
fixed set of four strings (`backend/app/schemas/goal.py:52-58`, `:95-100`,
mirrored in the `recurrence` column's DB enum at
`backend/app/models/goal.py:27-31`: `Enum("none", "daily", "weekly", "monthly",
name="recurrence")`). Nothing in the API surfaces that set. Today a client can
only learn the valid values by hard-coding them or by submitting a bad one and
reading the 422. A frontend building the "how often should this repeat?"
control needs the canonical list from the server, not a copy that can drift
from the schema silently.

This is deliberately the simple shape: a static, unauthenticated, side-effect-
free read. It exercises the acceptance-oracle chain's simple path end to end —
no entity to create, no prerequisite state, nothing that touches the database —
so a block on this story is attributable to the harness, not to setup
ambiguity. (Workstream D, `docs/BENCHMARK-READINESS-PLAN.md`: "D-1 … the simple
path end-to-end … purely additive.")

## Why `explore: false`

Set explicitly, not left to default. Under `explore: true` the SM persona emits
two competing full alternates for the same acceptance criteria, and
`superseded_by_sibling` on the loser is the normal, correct outcome — it is not
a build failure (measured 2026-08-08/09: 23 explore pairs → 23 deployed / 20
superseded). Mixing that normal-but-noisy outcome into an unattended,
three-story proof of the chain's *mechanics* would make a correct chain look
broken. `explore: false` gives this story a single SM decomposition and a
single oracle authored against `direction.acceptance` with no sibling to be
superseded by. The `explore: true` path is a separate, already-covered
question (Workstream A4) — not re-litigated here.

## Acceptance Criteria

- [ ] `GET /api/goals/recurrence-options` returns `200` with a JSON body whose
  `options` field is exactly the array `["none", "daily", "weekly", "monthly"]`
  — the same four values `POST /api/goals` and `PUT /api/goals/{id}` accept for
  `recurrence` (`backend/app/schemas/goal.py:55`, `:98`).
- [ ] The endpoint answers identically without any `Authorization` header: an
  unauthenticated `GET /api/goals/recurrence-options` also returns `200` with
  the same `options` body, so the frontend can populate the control before
  login exists.
- [ ] Sending a garbage `Authorization` header (e.g. `Bearer not-a-real-token`)
  does not change the response: it still returns `200` with the identical
  `options` body, never a `401` — demonstrating this is genuinely public
  reference data, not an authenticated route that happens to tolerate a bad
  token.

## Out of scope

- Any per-user or per-goal data. This is static reference data describing what
  the schema accepts; it must never vary by caller, environment, or existing
  goals.
- Changing `GET /api/goals/count` (already shipped, direction 120) or any other
  existing `/api/goals*` route's behavior. This is a new, additive route only.
- Frontend consumption. No UI wiring in this story.
- Changing the underlying `recurrence` enum itself. If a fifth value is ever
  added to the schema/DB enum, this endpoint must be updated in the same PR —
  but that is a future story, not this one.

## Context — a real routing hazard to avoid, verified against this app

`backend/app/routes/goals.py:163` registers `GET /{goal_id}` on the
`/api/goals`-prefixed router. FastAPI matches routes in registration order, so
any new `GET /api/goals/<literal-segment>` route added to that *same* router
**after** `/{goal_id}` is registered will never be reached — the literal
segment gets swallowed as a `goal_id` path parameter instead.

This is not hypothetical here: it is exactly why `GET /api/goals/count` lives
in its own file, `backend/app/routes/goal_count.py`, with its own
`APIRouter(prefix="/api/goals")`, included in `backend/app/main.py` at line 95
— **before** `goals_router` is included at line 96
(`backend/app/main.py:89-102`). The new route in this direction must be
registered the same way: either added to `goal_count.py`'s existing router (the
simplest option — it is already included before `goals_router`) or in its own
new file included before line 96. Do not add it directly to
`backend/app/routes/goals.py`'s `router` without moving it ahead of the
`/{goal_id}` registration.

## Expected size (pre-registered, for the benchmark record)

One vertical slice, one story. Concretely:

- New files: 1 (a test file, e.g. `backend/tests/test_goal_recurrence_options.py`).
- Modified files: 1 (`backend/app/routes/goal_count.py`, adding one route to the
  existing router — no `main.py` change needed, since that router is already
  included).
- Estimated sandbox iterations: comparable to direction 119 (build-metadata
  endpoint, 90) and 120 (goal-count endpoint, 60) — both single-file-addition,
  no-new-router stories of the same shape. Expect low double digits to ~90.

This is well inside the PM's per-story caps (`estimated_new_files ≤ 5`,
`estimated_modified_files ≤ 2`, `estimated_sandbox_iterations ≤ 200`,
`.claude/skills/new-direction/references/contract.md`) and inside the A4
single-story-per-AC-direction collapse thresholds (≤8 new / ≤6 modified files
summed across slices, ≤400 sandbox iterations) with wide margin — this
direction is not expected to produce more than one story, so collapse is moot,
but the margin is stated for the record.
