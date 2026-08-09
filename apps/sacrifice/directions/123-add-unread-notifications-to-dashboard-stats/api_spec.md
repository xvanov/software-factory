# API spec — dashboard stats unread-notification field

## GET /api/dashboard/stats **(existing — additive change)**

Authenticated. No query parameters, no request body. Unchanged request shape.

**Request:** `Authorization: Bearer <access_token>` header required (existing
behavior, unchanged).

**200 OK — new field added, all existing fields unchanged**

```json
{
  "total_goals": 1,
  "completed_count": 0,
  "failed_count": 0,
  "success_rate": 0.0,
  "total_pledged": 500,
  "total_donated": 0,
  "total_saved": 0,
  "unread_notifications": 1
}
```

| field | type | status |
|---|---|---|
| `total_goals` | integer | existing, unchanged |
| `completed_count` | integer | existing, unchanged |
| `failed_count` | integer | existing, unchanged |
| `success_rate` | float | existing, unchanged |
| `total_pledged` | integer (cents) | existing, unchanged |
| `total_donated` | integer (cents) | existing, unchanged |
| `total_saved` | integer (cents) | existing, unchanged |
| `unread_notifications` | integer | **new** — the caller's unread notification count, identical to `GET /api/notifications/unread-count`'s `unread_count` field for the same caller |

**401** — existing, unchanged behavior (`get_current_user` dependency). Not
introduced by this direction; not asserted in this direction's criteria.

## Setup used by the acceptance criteria (arrange, not assert)

1. `POST /api/auth/email/register` with a unique, `ACCEPTANCE_RUN_ID`-
   namespaced email. Response `200` with `AuthResponse
   {"access_token": <str>, "user": {...}}`. Use `access_token` as the bearer
   token for every subsequent call.
2. `GET /api/dashboard/stats` with that token → expect
   `unread_notifications == 0`, `total_goals == 0` (criterion 1).
3. `POST /api/goals` with that token and the body:
   ```json
   {
     "title": "<ACCEPTANCE_RUN_ID>-dashboard-unread-check",
     "deadline": "<now + 7 days, ISO-8601>",
     "pledge_amount": 500,
     "goal_type": "api_endpoint",
     "criteria": {"url": "https://example.com/health", "method": "GET", "expected_status": 200}
   }
   ```
   Response `201`. Fires one `goal_created` notification (existing behavior,
   `backend/app/routes/goals.py:139-146`), unread by default.
4. `GET /api/dashboard/stats` with that token again → expect
   `unread_notifications == 1` and `total_goals == 1` (criterion 2).
5. `GET /api/notifications/unread-count` with the same token → expect
   `unread_count == 1`, and assert it equals step 4's `unread_notifications`
   (criterion 3).

## Acceptance criteria — how each is observed

### 1. A fresh caller's `unread_notifications` is 0

- **Status:** graded by the acceptance oracle (HTTP)
- **How:** register (step 1), then `GET /api/dashboard/stats`. Assert `200`
  and `unread_notifications == 0`.
- **Endpoints:** `/api/auth/email/register`, `/api/dashboard/stats`

### 2. Creating a goal increases `unread_notifications` by exactly one, without disturbing `total_goals`

- **Status:** graded by the acceptance oracle (HTTP)
- **How:** steps 1-4. Assert the second `GET /api/dashboard/stats` call
  returns `unread_notifications == 1` AND `total_goals == 1` in the same
  response.
- **Endpoints:** `/api/auth/email/register`, `/api/goals`,
  `/api/dashboard/stats`

### 3. `unread_notifications` matches `GET /api/notifications/unread-count`'s value for the same caller

- **Status:** graded by the acceptance oracle (HTTP)
- **How:** step 5. Assert `GET /api/notifications/unread-count`'s
  `unread_count` field equals the `unread_notifications` value obtained in
  step 4, for the same access token.
- **Endpoints:** `/api/dashboard/stats`, `/api/notifications/unread-count`

## Observability affordances and their constraints

`unread_notifications` exposes only a count the caller can already obtain from
`GET /api/notifications/unread-count`. No new information is exposed to any
caller about any other user's data, and no existing field's value or type
changes.
