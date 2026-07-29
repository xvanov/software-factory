# Story

## Title
Add secure password reset and session revocation on reset — narrow read

## Scope
backend

## Story
As the backend auth system,
I want secure password-reset request and consume behavior with post-reset session revocation,
so that users can recover access without account-enumeration leaks and prior compromised sessions stop working.

# Acceptance Criteria

- [ ] Forgot-password issues expiring single-use reset tokens without disclosing account existence
- [ ] Reset endpoint enforces token validity, complexity checks, and attempt throttling
- [ ] Successful reset revokes prior active sessions/tokens

### Testable Claims (EARS)
AC1.1: WHEN the forgot-password endpoint is invoked, THE auth system SHALL issue a reset token that expires
AC1.2: WHEN the forgot-password endpoint is invoked, THE auth system SHALL make the reset token single-use
AC1.3: WHEN the forgot-password endpoint is invoked, THE auth system SHALL avoid disclosing account existence
AC2.1: WHEN the reset endpoint is invoked, THE auth system SHALL enforce reset-token validity
AC2.2: WHEN the reset endpoint is invoked, THE auth system SHALL enforce password complexity checks
AC2.3: WHEN the reset endpoint is invoked, THE auth system SHALL enforce attempt throttling
AC3.1: WHEN a password reset succeeds, THE auth system SHALL revoke prior active sessions/tokens

# Tasks / Subtasks

- [ ] Confirm existing auth/session invalidation primitives in `backend/app/routes/auth.py`, `backend/app/services/auth.py`, and `backend/app/core/dependencies.py`
- [ ] Add persistence for password reset tokens
  - [ ] Store token material in a form suitable for validation without plaintext token recovery
  - [ ] Store expiry metadata
  - [ ] Store single-use / consumed state
  - [ ] Associate token with user identity
- [ ] Add reset-token service contract
  - [ ] Generate reset token
  - [ ] Validate reset token
  - [ ] Mark token consumed on successful use
  - [ ] Reject expired token
  - [ ] Reject reused token
- [ ] Add forgot-password endpoint behavior
  - [ ] Accept email identifier input
  - [ ] Return enumeration-safe outward response for both existent and nonexistent accounts
  - [ ] Create expiring single-use token for existent accounts
- [ ] Add reset-password endpoint behavior
  - [ ] Accept reset token and new password input
  - [ ] Enforce token validity checks
  - [ ] Enforce password complexity checks using existing auth policy if present
  - [ ] Enforce attempt throttling with observable failure path
  - [ ] Update stored password on success
  - [ ] Mark reset token consumed on success
- [ ] Revoke sessions/tokens after successful password reset
  - [ ] Invalidate pre-reset bearer sessions/tokens
  - [ ] Ensure auth checks reject revoked pre-reset sessions/tokens
- [ ] Add backend tests
  - [ ] Token lifecycle tests: created, expires, single-use, consumed
  - [ ] Forgot-password tests: same outward response regardless of account existence
  - [ ] Reset tests: invalid token, expired token, reused token, complexity failure, throttling path
  - [ ] Session revocation tests: pre-reset token rejected after successful reset

# Dev Notes

[flow.md: see direction; none]

[api_spec.md: see direction; none]

## Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Stack]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/navigation.md#When working on replay defenses or session invalidation]
- [Source: context/current-state.md#Auth and identity]
- [Source: context/current-state.md#Security posture]
- [Source: context/modules/auth.md#Password authentication]
- [Source: context/modules/auth.md#OAuth and token exchange]
- [Source: context/modules/security.md#Authentication and token handling]
- [Source: context/modules/security.md#Known gaps]
- [Source: context/modules/backend.md#Auth routes and services]

## Direction acceptance criteria — verbatim embed
- [ ] Forgot-password issues expiring single-use reset tokens without disclosing account existence
- [ ] Reset endpoint enforces token validity, complexity checks, and attempt throttling
- [ ] Successful reset revokes prior active sessions/tokens

## Scope notes
- Narrow read: prepare one backend story that covers the full direction end-to-end, not the PM's four implementation slices as separate files.
- `flow.md` is absent in the direction.
- `api_spec.md` is absent in the direction.
- The direction explicitly identifies current lack of password reset as an auth hardening gap; keep implementation within auth/session surfaces and avoid unrelated auth redesign.
- Enumeration safety must be verified at the endpoint contract level; do not create divergent outward behavior by account existence.
- Single-use behavior must be persisted and testable, not implied.
- Throttling must have an observable enforcement path in tests.
- Session revocation must cover prior active bearer sessions/tokens, not merely changing the password hash.
- If existing password complexity policy is not centralized, implementation must use the current auth validation path rather than inventing a new policy outside auth.

# References

- `backend/app/routes/auth.py`
- `backend/app/services/auth.py`
- `backend/app/core/dependencies.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_email_auth.py`
- `backend/app/config.py`

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
