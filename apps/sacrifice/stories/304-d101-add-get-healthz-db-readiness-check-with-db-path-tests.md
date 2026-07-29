# Story

## Title
D101 add GET /healthz/db readiness check with DB path tests

## Story
**As a** platform/operator stakeholder
**I want** `GET /healthz/db` to verify actual database reachability with a trivial read
**so that** readiness signals reflect whether the app can serve DB-backed traffic.

## Acceptance Criteria
- [x] GET /healthz/db returns 200 with body {"db": "ok"} when the database is reachable.
- [x] GET /healthz/db returns 503 with body {"db": "unreachable"} when the DB round-trip fails.
- [x] The check performs only a trivial read (e.g. SELECT 1), never a write, and requires no auth.
- [x] A backend test covers both the healthy (200) and unreachable (503) paths.

### Testable Claims (EARS)
- AC1.1: WHEN `GET /healthz/db` is called, GIVEN the database is reachable, THE API SHALL respond with status `200` and body `{"db": "ok"}`.
- AC2.1: WHEN `GET /healthz/db` is called, GIVEN the DB round-trip fails, THE API SHALL respond with status `503` and body `{"db": "unreachable"}`.
- AC3.1: WHEN `GET /healthz/db` executes its readiness check, THE endpoint SHALL perform only a trivial read.
- AC3.2: WHEN `GET /healthz/db` executes its readiness check, THE endpoint SHALL never perform a write.
- AC3.3: WHEN `GET /healthz/db` is called, THE endpoint SHALL require no auth.
- AC4.1: WHEN backend automated tests run, THE test suite SHALL cover the healthy (`200`) path for `GET /healthz/db`.
- AC4.2: WHEN backend automated tests run, THE test suite SHALL cover the unreachable (`503`) path for `GET /healthz/db`.

## Tasks / Subtasks
- [x] Locate current health-check routing and readiness-related patterns.
- [x] Add unauthenticated `GET /healthz/db` route.
- [x] Implement trivial DB round-trip using read-only query (`SELECT 1`-style or equivalent).
- [x] Return `200` with `{"db": "ok"}` on successful round-trip.
- [x] Return `503` with `{"db": "unreachable"}` on DB round-trip failure.
- [x] Ensure failure handling covers raised DB-access errors without leaking internals.
- [x] Confirm endpoint performs no writes.
- [x] Confirm endpoint is excluded from auth dependencies.
- [x] Add backend test for reachable DB path.
- [x] Add backend test for unreachable DB path.
- [x] Run relevant backend tests for health/auth-adjacent routing.

## Dev Notes
### Scope notes
- Backend-only vertical slice.
- Story includes endpoint implementation and backend path tests in one shippable unit.
- No `flow.md` was provided in the direction.

### flow.md
(none)

### api_spec.md
# API spec

- `GET /healthz/db` -> 200 `{"db": "ok"}` when a `SELECT 1` round-trip to the database succeeds.
- `GET /healthz/db` -> 503 `{"db": "unreachable"}` when the database round-trip raises or times out.
- The endpoint is unauthenticated and performs no writes.

### Direction acceptance criteria (verbatim)
- [x] GET /healthz/db returns 200 with body {"db": "ok"} when the database is reachable.
- [x] GET /healthz/db returns 503 with body {"db": "unreachable"} when the DB round-trip fails.
- [x] The check performs only a trivial read (e.g. SELECT 1), never a write, and requires no auth.
- [x] A backend test covers both the healthy (200) and unreachable (503) paths.

### Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Stack]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/navigation.md#When working on replay defenses or session invalidation]

### Implementation pointers for Dev/Test Designer
- Existing app entrypoints and route registration likely live under backend FastAPI app wiring referenced from `backend/app/main.py` in project context.
- Endpoint must stay unauthenticated; verify no shared auth dependency is attached at router or route level.
- DB check must be a trivial read only; do not introduce writes, migrations, background jobs, or external service probes.
- Tests should isolate success vs. DB failure behavior at the HTTP contract boundary.
- If timeout behavior is already abstracted in current DB/session layer, reuse existing mechanism rather than inventing a parallel probe stack.

## References
- Direction: `direction.md`
- API contract: `api_spec.md`
- Tracker: `D101 add-a-database-readiness-healthz-endpoint`
- Story file path: `stories/304-d101-add-get-healthz-db-readiness-check-with-db-path-tests.md`

## Dev Agent Record
- Status: Implemented
- Implementation notes: Added unauthenticated `GET /healthz/db` route to `backend/app/routes/health.py` that performs `SELECT 1` via SQLAlchemy async session and returns 200 `{"db": "ok"}` or 503 `{"db": "unreachable"}` on exception. Five tests in `backend/tests/test_health.py` cover the healthy path, unreachable path (using dependency override with a mocked failing session), and no-auth requirement.
- Files changed: `backend/app/routes/health.py`, `backend/tests/test_health.py`
- Tests run: `tests/test_health.py` (5 passed), full suite `tests/` excluding e2e (740 passed, 1 skipped)

## Senior Developer Review
- Status: Pending
- Reviewer: _TBD_
- Review notes: _TBD_

## Review Follow-ups
- _None yet._
