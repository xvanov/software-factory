# Story

## Title
Verify and fix canonical OAuth login end-to-end on the deployed web app — broad read

## Summary
Prepare and land a reproducible deployed-web verification slice for canonical OAuth login that exercises the real browser callback path on the deployed origin, captures whether `auth_code` return, `/api/auth/exchange`, token persistence, authenticated state, and state-cookie honoring occur, and drives any minimally required fixes within test-owned harness/assertion coverage without weakening the existing auth_code + state-cookie CSRF hardening.

## Scope
`test`

# Acceptance Criteria

- [ ] Clicking 'Sign in with Google' on the deployed web app completes OAuth and ends authenticated (token stored, user loaded, no redirect-error banner).
- [ ] Clicking 'Sign in with GitHub' on the deployed web app completes OAuth and ends authenticated.
- [ ] After the provider redirect, the web client POSTs /api/auth/exchange with the ?auth_code= from the callback URL and stores the returned access_token.
- [ ] The OAuth state/CSRF cookie set at /api/auth/<provider>/login is present and honored on the callback on the deployed origin.
- [ ] A reproducible check (e2e spec or documented manual steps) demonstrates a full sign-in against the deployed instance.

### Testable Claims (EARS)
AC1.1: WHEN a desktop-browser user clicks 'Sign in with Google' on the deployed web app, THE deployed web app SHALL complete OAuth and end authenticated.
AC1.2: WHEN Google OAuth completes on the deployed web app, THE web client SHALL store the token.
AC1.3: WHEN Google OAuth completes on the deployed web app, THE web client SHALL load the user.
AC1.4: WHEN Google OAuth completes on the deployed web app, THE deployed web app SHALL show no redirect-error banner.
AC2.1: WHEN a desktop-browser user clicks 'Sign in with GitHub' on the deployed web app, THE deployed web app SHALL complete OAuth and end authenticated.
AC3.1: WHEN the provider redirects back with `?auth_code=` in the callback URL, THE web client SHALL POST `/api/auth/exchange` using that `auth_code`.
AC3.2: WHEN `/api/auth/exchange` returns `access_token`, THE web client SHALL store the returned `access_token`.
AC4.1: WHEN `/api/auth/<provider>/login` sets the OAuth state/CSRF cookie on the deployed origin, THE browser SHALL present that cookie on the callback on the deployed origin.
AC4.2: WHEN the callback is processed on the deployed origin, THE OAuth flow SHALL honor the state/CSRF cookie set at `/api/auth/<provider>/login`.
AC5.1: WHEN deployed OAuth verification is executed, THE system documentation or e2e coverage SHALL provide a reproducible full sign-in check against the deployed instance.

# Tasks / Subtasks

- [ ] Identify canonical deployed-web verification entrypoint and runner for browser-level auth checks.
- [ ] Add or update test harness to target deployed web origin without bypassing browser cookie behavior.
- [ ] Capture callback URL after provider return and assert `auth_code` presence.
- [ ] Observe and assert `/api/auth/exchange` POST occurs after callback.
- [ ] Assert returned `access_token` persistence through existing web auth storage path.
- [ ] Assert authenticated user state is loaded after exchange.
- [ ] Assert redirect-error banner is absent on successful completion.
- [ ] Cover Google sign-in path in deployed verification flow.
- [ ] Cover GitHub sign-in path in deployed verification flow.
- [ ] Capture evidence for state/CSRF cookie issuance at `/api/auth/<provider>/login`.
- [ ] Capture evidence that callback honors the issued state/CSRF cookie on deployed origin.
- [ ] If browser-level verification exposes a harness-layer gap, fix the verification harness only.
- [ ] If browser-level verification exposes app behavior and the change is required to make the reproducible check executable in this story scope, document exact failure handoff for backend/frontend child stories rather than broadening assertions.
- [ ] Record reproducible execution steps or fixture requirements for deployed verification.
- [ ] Keep assertions aligned with auth_code exchange + CSRF hardening; no token-in-redirect shortcuts.

# Dev Notes

## Flow Embed
No `flow.md` provided in direction.

## API Spec Embed
No `api_spec.md` provided in direction.

## Context Pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/navigation.md#When working on replay defenses or session invalidation]
- [Source: context/current-state.md#Authentication and session model]
- [Source: context/current-state.md#Frontend auth flow]
- [Source: context/current-state.md#OAuth and external identity]
- [Source: context/current-state.md#Testing and verification gaps]
- [Source: context/modules/auth.md#OAuth login and callback flow]
- [Source: context/modules/auth.md#Web auth_code exchange]
- [Source: context/modules/security.md#Bearer-token risk and CSRF/state expectations]
- [Source: context/modules/security.md#Cookie and origin considerations]
- [Source: context/modules/frontend.md#Web auth persistence and callback handling]
- [Source: context/modules/backend.md#Auth routes and exchange endpoint]

## Direction Acceptance Criteria (Verbatim Embed)
- [ ] Clicking 'Sign in with Google' on the deployed web app completes OAuth and ends authenticated (token stored, user loaded, no redirect-error banner).
- [ ] Clicking 'Sign in with GitHub' on the deployed web app completes OAuth and ends authenticated.
- [ ] After the provider redirect, the web client POSTs /api/auth/exchange with the ?auth_code= from the callback URL and stores the returned access_token.
- [ ] The OAuth state/CSRF cookie set at /api/auth/<provider>/login is present and honored on the callback on the deployed origin.
- [ ] A reproducible check (e2e spec or documented manual steps) demonstrates a full sign-in against the deployed instance.

## Implementation Notes for Dev/Test Design
- Story scope is `test`; primary deliverable is executable deployed-web verification coverage and/or reproducible operator check aligned to the PM first-step decomposition.
- Verification must exercise the real deployed origin and browser cookie policy; do not substitute local-only flows or direct token injection.
- Preserve the canonical auth shape already called out in project context: provider redirect returns one-time `auth_code`; frontend exchanges server-side; raw access tokens do not return from provider to frontend.
- Explicitly capture which layer fails if the flow does not complete: redirect URI/origin mismatch, missing state cookie, callback not triggering `/api/auth/exchange`, stale deployed frontend, or post-exchange persistence/user-load failure.
- Because this is the broad-read test story, include failure observability sufficient to unblock the backend/frontend follow-on child stories without re-diagnosing from scratch.
- Do not weaken CSRF/state protections in test setup. No bypass endpoints, no disabled cookie checks, no alternate callback contract.
- If provider credentials or fully automated third-party consent are unavailable in CI, the reproducible check may combine executable browser assertions around the deployed callback/exchange path with documented manual trigger points, but the resulting artifact must still satisfy the acceptance criterion requiring reproducibility.

# References

- Direction: `direction.md`
- PM decomposition context: `pm_result.child_stories`
- Canonical story template: `factory/artifacts/story_template.md`
- Likely code touchpoints called out by direction/context:
  - `frontend/services/auth.ts`
  - `frontend/hooks/useAuth.tsx`
  - `backend/app/routes/auth.py`
  - `backend/tests/test_auth.py`
  - `backend/tests/test_email_auth.py`

# Dev Agent Record

## Agent Model Used
- TBD

## Debug Log References
- TBD

## Completion Notes List
- TBD

## File List
- TBD

# Senior Developer Review

- TBD

# Review Follow-ups

- TBD
