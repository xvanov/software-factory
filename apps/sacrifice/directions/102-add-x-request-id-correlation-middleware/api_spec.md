# API spec — X-Request-ID correlation header

A single global HTTP middleware sets an `X-Request-ID` response header on
EVERY route and on error responses. Header-only: no auth, no database, no
request-body parsing.

- `GET /healthz` -> `200`, and the response includes an `X-Request-ID` header.
- When the request sends `X-Request-ID: client-supplied-123`, the `GET /healthz`
  `200` response echoes `X-Request-ID: client-supplied-123` verbatim.
- When the request omits `X-Request-ID`, the middleware generates a new UUIDv4
  and the `GET /healthz` `200` response returns it in the `X-Request-ID` header.
- `GET /does-not-exist` -> `404`, and the `404` response STILL includes an
  `X-Request-ID` header (the middleware wraps error responses too).
