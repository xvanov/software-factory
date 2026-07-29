# Story

**Title:** Add CSRF protections to cookie-authenticated API routes — broad read
**Slug:** add-csrf-protections-to-cookie-authenticated-api-routes-broa
**Scope:** backend

## Acceptance Criteria

- [ ] All state-changing authenticated routes reject requests without a valid CSRF token or equivalent protection.
- [ ] Session cookie settings are reviewed and hardened for SameSite, Secure, and HttpOnly semantics.

### Testable Claims (EARS)
AC1.1: WHEN a state-changing authenticated route receives a request without a valid CSRF token or equivalent protection, THE route SHALL reject the request
AC2.1: UNTESTABLE-AS-WRITTEN — missing required cookie names, target settings per environment, and observable review/hardening outcome for SameSite, Secure, and HttpOnly semantics

## Tasks / Subtasks

- [ ] Inventory cookie-authenticated API surface
  - [ ] Identify routes that authenticate via ambient cookie/session behavior rather than bearer-only auth
  - [ ] Classify authenticated state-changing endpoints by HTTP method and auth dependency path
  - [ ] Record any routes already protected by equivalent anti-forgery checks
- [ ] Implement reusable CSRF protection primitives
  - [ ] Add server-side CSRF validation dependency/middleware for cookie-authenticated requests
  - [ ] Define request token transport and validation path compatible with current FastAPI auth stack
  - [ ] Ensure safe methods remain unaffected unless existing auth logic requires otherwise
- [ ] Apply CSRF enforcement to route surface
  - [ ] Wire protection into all cookie-authenticated state-changing routes discovered in inventory
  - [ ] Preserve non-cookie bearer-token flows unless they are also cookie-authenticated
  - [ ] Return consistent rejection behavior for missing/invalid protection
- [ ] Harden session cookie attributes
  - [ ] Review current cookie issuance path(s) in auth/session code
  - [ ] Set or confirm SameSite semantics on session cookies
  - [ ] Set or confirm Secure semantics on session cookies
  - [ ] Set or confirm HttpOnly semantics on session cookies
- [ ] Add automated backend coverage
  - [ ] Unit/integration tests for CSRF primitive acceptance/rejection behavior
  - [ ] Route-level tests proving protected state-changing endpoints reject missing/invalid CSRF protection
  - [ ] Tests asserting cookie security attributes on emitted session cookies
- [ ] Validate scope boundaries
  - [ ] Do not redesign auth architecture beyond cookie-authenticated route protection
  - [ ] Do not broaden to non-cookie auth mechanisms except where shared code paths require compatibility

## Dev Notes

### Scope and sequencing
- Broad-read story covering the full direction outcome in one backend slice: reusable guard, route enforcement, cookie hardening, and backend tests.
- PM decomposition context indicates narrower child stories exist, but this story is intentionally the single-source broad slice for this assigned record.

### flow.md
(none)

### api_spec.md
(none)

### Direction acceptance criteria (verbatim)
- [ ] All state-changing authenticated routes reject requests without a valid CSRF token or equivalent protection.
- [ ] Session cookie settings are reviewed and hardened for SameSite, Secure, and HttpOnly semantics.

### Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Stack]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/navigation.md#When working on replay defenses or session invalidation]

### Implementation context for Dev/Test-Designer
- Current-state prelude says bearer-token compromise is already treated as high impact and that shared auth dependencies reach multiple backend routes; inspect auth dependencies before route wiring.
- Current-state prelude says OAuth browser/mobile flows redirect with a one-time `auth_code`, not raw access tokens; preserve that behavior while evaluating whether any browser session/cookie flows exist today.
- Current-state prelude explicitly notes: "Explore is enabled, so downstream can inspect the current auth/session surface to determine which routes are actually cookie-authenticated today." Treat route inventory as required first step.
- Acceptance criterion 1 allows "valid CSRF token or equivalent protection". If implementation relies on an equivalent anti-forgery control for some route(s), tests must prove rejection without that protection and story review must confirm equivalence is explicit, not implicit.
- Acceptance criterion 2 is under-specified for environment-specific semantics. Reviewer should confirm the implemented SameSite/Secure/HttpOnly policy matches the app's actual deployment assumptions and existing cookie issuance paths.
- If no cookie-authenticated state-changing routes exist after inventory, implementation must still make the finding explicit in tests/docs/review evidence and harden any session cookie issuance path that does exist; do not silently no-op.

## References

- Direction: `direction.md`
- PM decomposition context: `pm_result.child_stories`
- Candidate code entrypoints named in current-state context:
  - `backend/app/routes/auth.py`
  - `backend/app/services/auth.py`
  - `backend/app/core/dependencies.py`
  - `backend/tests/test_auth.py`
  - `backend/tests/test_email_auth.py`

## Dev Agent Record

- Status: Not started
- Implementation notes: TBD by Dev
- Test evidence: TBD by Dev
- Files changed: TBD by Dev

## Senior Developer Review

- Review status: Pending
- Checklist:
  - [ ] Inventory proves which routes are cookie-authenticated
  - [ ] Every in-scope state-changing authenticated route is covered by rejection tests
  - [ ] Rejection behavior is consistent for missing/invalid CSRF protection
  - [ ] Cookie issuance paths assert SameSite/Secure/HttpOnly semantics
  - [ ] No unintended regression to bearer-token auth flows
  - [ ] Any claimed "equivalent protection" is explicit and test-backed

## Review Follow-ups

- None yet
