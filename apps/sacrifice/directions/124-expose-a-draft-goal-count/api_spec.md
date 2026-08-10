# API spec — draft goal count

## GET /api/goals/draft-count **(new)**

Authenticated. No query parameters, no request body.

**Request:** `Authorization: Bearer <access_token>` header required.

**200 OK**

```json
{
  "count": 0
}
```

| field | type | constraint |
|---|---|---|
| `count` | integer | the caller's own count of goals in `draft` status; non-negative |

**401** — no `Authorization` header, expired token, malformed token, or empty
token string. Assert status code only; do not assert the body (this direction
did not introduce `get_current_user`, so it cannot state what that
dependency's error body says).

## Setup used by the acceptance criteria (arrange, not assert)

1. `POST /api/auth/email/register` with a unique, `ACCEPTANCE_RUN_ID`-
   namespaced email and a policy-passing password (derive it at runtime, e.g.
   `f"Ok-{uuid.uuid4().hex}"` — the app rejects common and all-digit
   passwords with `400`). Response `200` with
   `{"access_token": <str>, "user": {...}}`. Use `access_token` as the bearer
   token for every subsequent call in this story.
2. `GET /api/goals/draft-count` with that token → expect `{"count": 0}`
   (criterion 1).
3. `POST /api/goals` with that token and the body:
   ```json
   {
     "title": "<ACCEPTANCE_RUN_ID>-draft-count-check",
     "deadline": "<now + 7 days, ISO-8601, computed at runtime>",
     "pledge_amount": 500,
     "goal_type": "api_endpoint",
     "criteria": {"url": "https://example.com/health", "method": "GET", "expected_status": 200}
   }
   ```
   Response `201`; the goal is created in `draft` status (the default —
   `GoalCreate` has no `status` field).
4. `GET /api/goals/draft-count` with that token again → expect
   `{"count": 1}` (criterion 2).

All arrange calls use routes that exist at the merge base; only the assert
calls touch the new route.

## Acceptance criteria — how each is observed

### 1. A fresh caller's draft count is 0

- **Status:** graded by the acceptance oracle (HTTP)
- **How:** register (step 1 above), then `GET /api/goals/draft-count`.
  Assert `200` and body exactly `{"count": 0}`.
- **Endpoints:** `/api/auth/email/register`, `/api/goals/draft-count`

### 2. Creating a goal increases the draft count by exactly one

- **Status:** graded by the acceptance oracle (HTTP)
- **How:** steps 1-4 above. Assert the second `GET /api/goals/draft-count`
  returns `200` with body exactly `{"count": 1}`.
- **Endpoints:** `/api/auth/email/register`, `/api/goals`,
  `/api/goals/draft-count`

### 3. An unauthenticated request is rejected

- **Status:** graded by the acceptance oracle (HTTP)
- **How:** `GET /api/goals/draft-count` with no `Authorization` header.
  Assert status `401`. Do not assert the response body.
- **Endpoints:** `/api/goals/draft-count`

## Observability affordances and their constraints

None introduced beyond the `count` field itself, which exposes only a number
already fully derivable by the caller paging their own `GET /api/goals` — no
new information leaks about any other user's data.
