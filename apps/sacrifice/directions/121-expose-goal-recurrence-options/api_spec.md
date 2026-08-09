# API spec — goal recurrence options

## GET /api/goals/recurrence-options **(new)**

Unauthenticated or authenticated — the response must be identical either way.
No query parameters, no request body, no side effects, no database access.

**200 OK**

```json
{
  "options": ["none", "daily", "weekly", "monthly"]
}
```

| field | type | constraint |
|---|---|---|
| `options` | array of string | exactly `["none", "daily", "weekly", "monthly"]`, in this order |

Notes:

- These are the exact four values `POST /api/goals` and `PUT /api/goals/{id}`
  accept for the `recurrence` field, verified against
  `backend/app/schemas/goal.py:52-58` (`GoalCreate.validate_recurrence`) and
  `:95-100` (`GoalUpdate.validate_recurrence`), and against the DB column enum
  at `backend/app/models/goal.py:27-31`. Do not invent a fifth value or a
  different order; if the schema ever adds one, this endpoint changes in the
  same PR that adds it.
- No `Authorization` header is required or honoured. Sending one — even an
  invalid one — must not change the response or its status code.
- This endpoint must not query the database. It returns a fixed literal.
- Additional response fields are permitted but must contain no user data, no
  per-goal data, and nothing that varies by caller or environment.

**Errors**

None expected. This endpoint reads no external state and has no auth
dependency, so it has no failure mode of its own.

**Routing hazard — read before implementing**

Register this route on a router that FastAPI includes **before**
`goals_router` (`backend/app/main.py:96`), never as a route added to
`goals_router` itself after `GET /{goal_id}` (`backend/app/routes/goals.py:163`)
is registered on it — a literal path segment registered after a `{goal_id}`
catch-all on the *same* router is unreachable; it is captured as a `goal_id`
first. `backend/app/routes/goal_count.py`'s router is already included at
`main.py:95`, one line before `goals_router` at `main.py:96`, for exactly this
reason (`GET /api/goals/count`). Reusing that router is the simplest correct
option.

## Acceptance criteria — how each is observed

### 1. `GET /api/goals/recurrence-options` returns the exact options array

- **How:** `GET /api/goals/recurrence-options` with no `Authorization` header.
  Assert status `200` and body exactly `{"options": ["none", "daily", "weekly",
  "monthly"]}`.
- **Endpoints:** `/api/goals/recurrence-options`

### 2. The endpoint requires no authentication

- **How:** Same request as above, asserting the same body without ever having
  obtained an access token. (This criterion and #1 are observed by the same
  call — the point is that no `Authorization` header was needed to get `200`.)
- **Endpoints:** `/api/goals/recurrence-options`

### 3. An invalid `Authorization` header does not change the response

- **How:** `GET /api/goals/recurrence-options` with header
  `Authorization: Bearer not-a-real-token`. Assert status `200` and the
  identical `options` body — never `401`.
- **Endpoints:** `/api/goals/recurrence-options`

## Observability affordances and their constraints

None introduced. This is static reference data with no relationship to any
caller, session, or stored entity.
