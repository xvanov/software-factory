# API spec — notification total count

## GET /api/notifications/count **(new)**

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
| `count` | integer | the caller's own total notification count (all types, read and unread); non-negative |

**401** — no `Authorization` header, expired token, malformed token, or empty
token string. Assert status code only; do not assert the body (see "the 401
body" note in `d2.md` — this direction did not introduce `get_current_user`,
so it cannot state what that dependency's error body says).

## Setup used by the acceptance criteria (arrange, not assert)

1. `POST /api/auth/email/register` with a unique, `ACCEPTANCE_RUN_ID`-
   namespaced email and a password ≥8 chars
   (`backend/app/schemas/auth.py:4-8`, `EmailRegisterRequest`). Response `200`
   with `AuthResponse {"access_token": <str>, "user": {...}}`
   (`backend/app/routes/auth.py:55-58`). Use `access_token` as the bearer token
   for every subsequent call in this story.
2. `GET /api/notifications/count` with that token → expect `{"count": 0}`
   (criterion 1).
3. `POST /api/goals` with that token and the body:
   ```json
   {
     "title": "<ACCEPTANCE_RUN_ID>-notif-count-check",
     "deadline": "<now + 7 days, ISO-8601>",
     "pledge_amount": 500,
     "goal_type": "api_endpoint",
     "criteria": {"url": "https://example.com/health", "method": "GET", "expected_status": 200}
   }
   ```
   Response `201`. This fires exactly one `goal_created` notification
   (`backend/app/routes/goals.py:139-146`), which is EXISTING behavior — no
   code change makes this happen, it already does.
4. `GET /api/notifications/count` with that token again → expect
   `{"count": 1}` (criterion 2).

## Acceptance criteria — how each is observed

### 1. A fresh caller's notification count is 0

- **Status:** graded by the acceptance oracle (HTTP)
- **How:** register (step 1 above), then `GET /api/notifications/count`.
  Assert `200` and body exactly `{"count": 0}`.
- **Endpoints:** `/api/auth/email/register`, `/api/notifications/count`

### 2. Creating a goal increases the count by exactly one

- **Status:** graded by the acceptance oracle (HTTP)
- **How:** steps 1-4 above. Assert the second `GET /api/notifications/count`
  returns `200` with body exactly `{"count": 1}`.
- **Endpoints:** `/api/auth/email/register`, `/api/goals`,
  `/api/notifications/count`

### 3. An unauthenticated request is rejected

- **Status:** graded by the acceptance oracle (HTTP)
- **How:** `GET /api/notifications/count` with no `Authorization` header.
  Assert status `401`. Do not assert the response body.
- **Endpoints:** `/api/notifications/count`

## Observability affordances and their constraints

None introduced beyond the `count` field itself, which exposes only a number
already fully derivable by the caller paging their own `GET
/api/notifications` — no new information leaks to a caller about any other
user's data.
