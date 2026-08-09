# API contract — Expose a goal-count endpoint for the authenticated user

> Authored by the `contract` persona from the direction's acceptance
> criteria and the app's REAL route table. This file is the shared
> contract: the implementer builds to it and the independent acceptance
> oracle grades against it. Paths here are exact.

## Endpoints

### `GET /api/goals/count` **(new)**

Return the authenticated user's total goal count as a JSON integer field, supporting criteria 1-3.

- **Request:** Authorization: Bearer <access_token> header required; no query parameters or body
- **Response:** 200 {"count": <integer>}
- **Status codes:**
  - `200` — Authenticated request with a valid access token. Returns the caller's own goal total (may be zero). → body: `{"count": <non-negative integer>}`
  - `401` — No Authorization header present, expired token, malformed token, or empty token string. → body: `(existing app behaviour — assert the status code only, not the body)`

## Acceptance criteria — how each is observed

### 1. GET /api/goals/count returns the authenticated caller's own goal total as a JSON integer field

- **Status:** graded by the acceptance oracle (HTTP)
- **How:** Register a new user via POST /api/auth/email/register with unique email and obtain access_token, then GET /api/goals/count with Authorization: Bearer <access_token>. Assert response status is 200 and body is exactly {"count": <integer>}.
- **Endpoints:** `/api/goals/count`, `/api/auth/email/register`

### 2. The count reflects goals the caller creates: creating a goal increases it by exactly one

- **Status:** graded by the acceptance oracle (HTTP)
- **How:** Register a new user via POST /api/auth/email/register and obtain access_token. GET /api/goals/count to record initial count. POST /api/goals to create a goal for that user with Authorization: Bearer <access_token>. GET /api/goals/count again and assert the count equals initial_count + 1. Repeat to verify idempotent incrementing.
- **Endpoints:** `/api/goals/count`, `/api/auth/email/register`, `/api/goals`

### 3. An unauthenticated request is rejected rather than returning a count

- **Status:** graded by the acceptance oracle (HTTP)
- **How:** Send GET /api/goals/count with no Authorization header. Assert response status is 401 and body contains {"detail": "Unauthorized"}.
- **Endpoints:** `/api/goals/count`

## Observability affordances and their constraints

No observability affordances introduced. The endpoint itself serves only the caller's own count and carries no information an authenticated user cannot already derive from GET /api/goals.

## Operator ratification — 2026-08-09

Corrected after the acceptance gate blocked a CORRECT pull request (story 179,
sacrifice PR #395). Six gates passed; `acceptance-verified` failed with
`exit_code=1 (assertion failed at HEAD)`.

The 401 body was invented. The app's `get_current_user` has raised
`401 {"detail": "Invalid or expired token"}` since long before this direction;
the contract asserted `{"detail": "Unauthorized"}`, the oracle enforced that
literally, and dev — which correctly reused the existing dependency — could
never satisfy it. The implementation was right and the spec was wrong.

Generalised into `contract` rule 2d and the `acceptance_author` persona in
factory PR #277: for an error path this direction did not introduce, assert the
status code and never the body, because the route table supplies paths and
cannot supply the error wording raised inside shared dependencies.
