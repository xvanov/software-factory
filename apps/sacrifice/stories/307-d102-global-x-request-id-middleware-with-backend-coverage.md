# Story

## Story
As a backend maintainer and API consumer,
I want every HTTP response to carry a stable `X-Request-ID`,
so requests can be correlated across middleware, handlers, and failures.

## Acceptance Criteria
- [ ] A GET to an existing endpoint (e.g. /healthz) returns a response containing an X-Request-ID header.
- [ ] When the request includes an X-Request-ID header, the response echoes that exact value.
- [ ] When the request omits X-Request-ID, the response contains a newly generated valid UUIDv4.
- [ ] The header is present on non-2xx responses as well (e.g. a 404).
- [ ] A backend test in tests/ covers echo, generation, and presence on a 404.

### Testable Claims (EARS)
AC1.1: WHEN a client sends GET `/healthz`, THE backend SHALL return a response containing an `X-Request-ID` header.
AC2.1: WHEN a request includes an `X-Request-ID` header, THE backend SHALL return a response whose `X-Request-ID` header exactly matches the request header value.
AC3.1: WHEN a request omits `X-Request-ID`, THE backend SHALL return a response containing a newly generated valid UUIDv4 in the `X-Request-ID` header.
AC4.1: WHEN the backend returns a non-2xx response, THE backend SHALL include an `X-Request-ID` header in that response.
AC4.2: WHEN a client sends GET to a non-existent route, THE backend SHALL return a `404` response containing an `X-Request-ID` header.
AC5.1: WHEN backend automated tests run, THE test suite SHALL include coverage for request-id echo behavior.
AC5.2: WHEN backend automated tests run, THE test suite SHALL include coverage for generated request-id behavior.
AC5.3: WHEN backend automated tests run, THE test suite SHALL include coverage for `X-Request-ID` presence on a `404` response.

## Tasks / Subtasks
- [ ] Identify FastAPI app entrypoint and current middleware registration path.
- [ ] Add global HTTP middleware for `X-Request-ID` response handling.
- [ ] Read incoming `X-Request-ID` request header when present.
- [ ] Echo caller-supplied header value verbatim on response.
- [ ] Generate UUIDv4 when request header is absent.
- [ ] Ensure middleware applies to existing success responses.
- [ ] Ensure middleware applies to framework-generated non-2xx responses, including `404`.
- [ ] Add or update backend tests under `backend/tests/`.
- [ ] Cover `/healthz` header presence.
- [ ] Cover `/healthz` caller-supplied header echo.
- [ ] Cover `/healthz` generated UUIDv4 path.
- [ ] Cover `404` header presence.
- [ ] Confirm no auth, DB, or request-body coupling is introduced.

## Dev Notes
### Scope notes
- Single vertical slice: one global backend middleware plus backend coverage proving the observable contract.
- `flow.md` is absent for this direction.
- Direction acceptance criteria are explicit; do not expand scope beyond header propagation on HTTP responses.

### Verbatim direction acceptance criteria
- [ ] A GET to an existing endpoint (e.g. /healthz) returns a response containing an X-Request-ID header.
- [ ] When the request includes an X-Request-ID header, the response echoes that exact value.
- [ ] When the request omits X-Request-ID, the response contains a newly generated valid UUIDv4.
- [ ] The header is present on non-2xx responses as well (e.g. a 404).
- [ ] A backend test in tests/ covers echo, generation, and presence on a 404.

### flow.md
(none)

### api_spec.md
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

### Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Stack]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/navigation.md#When working on replay defenses or session invalidation]

### Implementation guardrails
- Global HTTP middleware only; no endpoint-specific patching.
- Header-only behavior; no auth, database, request-body parsing, or Celery involvement.
- Preserve exact caller-supplied header value when present.
- Generated value must be valid UUIDv4 when header absent.
- Response header must exist on framework-generated error responses, including `404`.
- Backend tests should assert observable response headers, not internal implementation details.

## References
- `backend/app/main.py`
- `backend/tests/`
- `backend/tests/test_auth.py`
- `backend/app/core/dependencies.py`

## Dev Agent Record
### Agent Model Used
- TBD

### Debug Log References
- TBD

### Completion Notes List
- TBD

### File List
- TBD

## Senior Developer Review
- TBD

## Review Follow-ups
- TBD
