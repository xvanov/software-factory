# Story

## Title
Add CSRF protections to cookie-authenticated API routes — narrow read

## Story
**As a** backend engineer
**I want** cookie-authenticated API routes to enforce explicit CSRF protections and hardened session cookie attributes
**so that** authenticated browser requests cannot rely on ambient cookies alone to perform state-changing actions.

## Acceptance Criteria
- [ ] All state-changing authenticated routes reject requests without a valid CSRF token or equivalent protection.
- [ ] Session cookie settings are reviewed and hardened for SameSite, Secure, and HttpOnly semantics.

### Testable Claims (EARS)
AC1.1: WHEN a request targets a state-changing authenticated route without a valid CSRF token or equivalent protection, THE route SHALL reject the request
AC2.1: WHEN session cookie settings are configured for authenticated cookie flows, THE session cookie implementation SHALL be reviewed for SameSite semantics
AC2.2: WHEN session cookie settings are configured for authenticated cookie flows, THE session cookie implementation SHALL be hardened for SameSite semantics
AC2.3: WHEN session cookie settings are configured for authenticated cookie flows, THE session cookie implementation SHALL be reviewed for Secure semantics
AC2.4: WHEN session cookie settings are configured for authenticated cookie flows, THE session cookie implementation SHALL be hardened for Secure semantics
AC2.5: WHEN session cookie settings are configured for authenticated cookie flows, THE session cookie implementation SHALL be reviewed for HttpOnly semantics
AC2.6: WHEN session cookie settings are configured for authenticated cookie flows, THE session cookie implementation SHALL be hardened for HttpOnly semantics

## Tasks / Subtasks
- [ ] Identify current cookie-authenticated routes and auth dependencies in backend auth/session handling
- [ ] Define narrow-read route inventory limited to routes that already authenticate via cookies or session semantics
- [ ] Add reusable backend CSRF validation primitive for cookie-authenticated requests
- [ ] Wire CSRF enforcement into state-changing authenticated routes within the narrow-read inventory
- [ ] Preserve non-cookie bearer-token flows unless they already participate in cookie-authenticated behavior
- [ ] Add/extend backend tests covering rejection for missing CSRF protection on covered state-changing routes
- [ ] Add/extend backend tests covering rejection for invalid CSRF protection on covered state-changing routes
- [ ] Review session cookie issuance/configuration path for SameSite semantics
- [ ] Review session cookie issuance/configuration path for Secure semantics
- [ ] Review session cookie issuance/configuration path for HttpOnly semantics
- [ ] Harden session cookie settings where current implementation is weaker than the direction requires
- [ ] Verify tests assert observable cookie attribute behavior where cookies are issued
- [ ] Document any route inventory exclusions in Dev Agent Record if no cookie-authenticated mutating routes exist outside auth/session paths

## Dev Notes
- Narrow read scope: implement only for API surfaces that are actually cookie-authenticated today. Do not broaden to all authenticated bearer-token routes unless inspection shows those routes accept ambient browser cookies as auth.
- PM decomposition context: this single story file covers the direction narrowly rather than emitting separate child-story files. Sequence still matters: reusable guard, route enforcement, cookie hardening, then docs.
- [flow.md: see none provided in direction]
- [api_spec.md: see none provided in direction]

### Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/navigation.md#When working on replay defenses or session invalidation]
- [Source: context/modules/auth.md]
- [Source: context/modules/security.md]
- [Source: context/modules/backend.md]
- [Source: context/current-state.md#auth]
- [Source: context/current-state.md#security]

### Direction acceptance criteria (verbatim)
- [ ] All state-changing authenticated routes reject requests without a valid CSRF token or equivalent protection.
- [ ] Session cookie settings are reviewed and hardened for SameSite, Secure, and HttpOnly semantics.

### Implementation notes
- Current project context says OAuth browser/mobile flows return a one-time `auth_code` and clients exchange server-side for the bearer token; inspect whether any backend routes also maintain cookie-authenticated session behavior before expanding enforcement.
- Token handling is already treated as high impact; avoid weakening existing bearer-token auth dependencies while adding cookie-path CSRF checks.
- Prefer a reusable dependency/middleware/helper over per-route bespoke checks.
- Rejection behavior must be observable in tests for missing and invalid CSRF protection.
- Cookie hardening work is limited to SameSite, Secure, and HttpOnly semantics; no broad auth redesign.
- If inspection finds no current cookie-authenticated mutating routes beyond auth/session endpoints, record that explicitly and keep scope constrained to those actual surfaces.

## References
- `backend/app/routes/auth.py`
- `backend/app/services/auth.py`
- `backend/app/core/dependencies.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_email_auth.py`
- `backend/app/config.py`
- `frontend/services/auth.ts`
- `context/project.md`
- `context/navigation.md`

## Dev Agent Record
- Status: Not started
- Route inventory reviewed:
- CSRF mechanism selected:
- Cookie issuance/configuration touchpoints:
- Tests added/updated:
- Notes on excluded routes:

## Senior Developer Review
- Pending

## Review Follow-ups
- None yet
