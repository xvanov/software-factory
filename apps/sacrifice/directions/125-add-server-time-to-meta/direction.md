---
title: Add server_time to the build metadata endpoint
type: feature
priority: p2
explore: false
created_at: '2026-08-10T12:00:00+00:00'
related_directions: []
---

# Add `server_time` to `GET /api/meta`

## Why

`GET /api/meta` (direction 119, deployed via story 172) returns
`{"service": "sacrifice", "version": "0.1.0"}` — static build facts. Clients
that cache the payload have no way to tell a fresh response from a stale one,
and support diagnostics ("is the backend clock sane?") need a
server-timestamp probe. Adding a `server_time` field — the server's current
UTC time in ISO-8601 — makes the endpoint self-dating with a one-line change.

This is a fresh Workstream D-3 shape (a change to an EXISTING endpoint's
response) — the re-proof after the 2026-08-10 abort. The prior D-3
(direction 123, story 186) parked on an ORACLE-AUTHOR defect (a
`@pytestFixture` typo the vacuity control correctly refused), not on the
chain or this shape. The authoring-time `pytest --collect-only` smoke that
kills that class mechanically is merged; this direction is its fresh,
unattended validation.

## Why `explore: false`

Same reasoning as directions 121-123 (see direction 124).

## Acceptance Criteria

- [ ] `GET /api/meta` (unauthenticated, as today) returns `200` and the body
  still contains `"service": "sacrifice"` and a non-empty string `"version"`
  — the existing contract is unchanged.
- [ ] The body additionally contains `"server_time"`: a string parseable as
  an ISO-8601 timestamp with an explicit UTC offset (i.e.
  `datetime.fromisoformat(value)` succeeds and the parsed value is
  timezone-aware).
- [ ] Two consecutive `GET /api/meta` calls both return `200` with a valid
  `server_time` (the field is computed per-request, not a crash-once static).

## Out of scope

- Any other new field on `/api/meta` (uptime, git sha, environment name).
- Any change to `/api/health`, `/healthz`, or `/healthz/db`.
- Clock-accuracy assertions (no comparison of `server_time` against the
  caller's clock — clock skew is not this direction's business; parseability
  and timezone-awareness are the observables).

## Blast radius — pre-registered (Workstream D discipline)

`grep -rl "api/meta" backend/tests/` at authoring time: **1 file**
(`test_meta.py`). Pre-registered bound: ≤3 test files touched. The
implementation is a one-line addition inside
`backend/app/routes/meta.py`'s existing handler — no new route, no auth, no
database.

## Oracle discipline

The arrange step for this direction is empty — `/api/meta` needs no account
and no entities (KNOWN OPEN #5 is moot here). Do not assert exact equality of
`server_time` across calls or against a fixed literal: it changes per
request by design. The vacuity control still bites: "field present and
parseable" fails against both stub variants (which answer `200 {}`), so the
criterion is credited, and it fails at the merge base (where the field does
not exist), so the base run discriminates.
