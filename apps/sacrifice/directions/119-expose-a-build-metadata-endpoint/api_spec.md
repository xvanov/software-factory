# API spec — build-metadata endpoint

## GET /api/meta

Unauthenticated. No query parameters, no request body, no side effects.

**200 OK**

```json
{
  "service": "sacrifice",
  "version": "0.1.0"
}
```

| field | type | constraint |
|---|---|---|
| `service` | string | exactly `"sacrifice"` |
| `version` | string | non-empty; identifies the running build |

Notes:

- `service` is a fixed literal, not derived from configuration — a caller uses it
  to confirm *which application* answered, so it must not vary by environment.
- `version` may be a module-level constant. It must be non-empty. Do not invoke
  `git` at request time.
- No `Authorization` header is required or honoured. Sending one must not change
  the response.
- Additional fields are permitted but must contain no user data, secrets,
  environment variables, or database contents.

**Errors**

None expected. This endpoint reads no external state, so it has no failure mode
of its own; it must not touch the database.
