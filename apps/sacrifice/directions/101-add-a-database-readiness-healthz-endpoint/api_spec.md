# API spec

- `GET /healthz/db` -> 200 `{"db": "ok"}` when a `SELECT 1` round-trip to the database succeeds.
- `GET /healthz/db` -> 503 `{"db": "unreachable"}` when the database round-trip raises or times out.
- The endpoint is unauthenticated and performs no writes.
