# API spec — server_time on the build metadata endpoint

## GET /api/meta **(existing — one field added)**

Unauthenticated, as today. No query parameters, no request body.

**200 OK**

```json
{
  "service": "sacrifice",
  "version": "0.1.0",
  "server_time": "2026-08-10T12:34:56.789012+00:00"
}
```

| field | type | constraint |
|---|---|---|
| `service` | string | unchanged: exactly `"sacrifice"` |
| `version` | string | unchanged: non-empty |
| `server_time` | string | **new**: the server's current UTC time, ISO-8601 with an explicit UTC offset; `datetime.fromisoformat` must parse it to a timezone-aware value; computed per request |

No error responses change. The route has no auth and no failure modes of its
own beyond process death (covered by criterion 3's second call).

## Acceptance criteria — how each is observed

### 1. The existing contract is unchanged

- **Status:** graded by the acceptance oracle (HTTP)
- **How:** `GET /api/meta`. Assert `200`, body `"service" == "sacrifice"`,
  and `"version"` is a non-empty string.
- **Endpoints:** `/api/meta`

### 2. `server_time` is present and a timezone-aware ISO-8601 timestamp

- **Status:** graded by the acceptance oracle (HTTP)
- **How:** same response. Assert `"server_time"` is a string,
  `datetime.fromisoformat(value)` succeeds, and the parsed value's
  `tzinfo` is not `None`.
- **Endpoints:** `/api/meta`

### 3. The field is computed per request, not a crash-once static

- **Status:** graded by the acceptance oracle (HTTP)
- **How:** a second `GET /api/meta`. Assert `200` and a valid `server_time`
  again. Do NOT assert the two values differ (two calls inside the same
  clock tick may legitimately be equal) and do NOT compare against the
  caller's own clock.
- **Endpoints:** `/api/meta`

## Setup used by the acceptance criteria

None. The endpoint is unauthenticated and stateless — there is no arrange
step (and therefore nothing for KNOWN OPEN #5 to bite on).

## Observability affordances and their constraints

`server_time` exposes only the server's wall clock, which every `Date`
response header already leaks. No user data is involved.
