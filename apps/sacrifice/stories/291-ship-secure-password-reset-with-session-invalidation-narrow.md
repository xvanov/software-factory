# Story

## Story
As a Sacrifice backend maintainer,
I want a secure email/password reset flow that issues expiring single-use reset tokens, returns generic request responses, confirms resets safely, and revokes existing bearer sessions on success,
so compromised users can recover access without account enumeration or stale-session exposure.

## Acceptance Criteria
- [ ] Reset request/confirm endpoints use expiring single-use tokens with generic responses
- [ ] Successful reset revokes existing sessions/bearers for that user
- [ ] Tests verify token expiry, replay rejection, and anti-enumeration behavior

### Testable Claims (EARS)
AC1.1: WHEN a password reset is requested, THE reset request endpoint SHALL use expiring single-use tokens
AC1.2: WHEN a password reset is confirmed, THE reset confirm endpoint SHALL use expiring single-use tokens
AC1.3: WHEN a password reset is requested, THE reset request endpoint SHALL return a generic response
AC1.4: WHEN a password reset is confirmed, THE reset confirm endpoint SHALL return a generic response
AC2.1: WHEN a password reset succeeds, THE auth/session system SHALL revoke existing sessions/bearers for that user
AC3.1: WHEN auth-route tests are executed, THE test suite SHALL verify token expiry behavior
AC3.2: WHEN auth-route tests are executed, THE test suite SHALL verify replay rejection behavior
AC3.3: WHEN auth-route tests are executed, THE test suite SHALL verify anti-enumeration behavior

## Tasks / Subtasks
- [ ] Define backend reset-token persistence and service primitive
  - [ ] Add expiring token fields and single-use/consumed state
  - [ ] Bind token records to email/password-capable user accounts
  - [ ] Ensure lookup path supports expiry and consumed checks
- [ ] Add password reset request endpoint behavior
  - [ ] Accept email/password recovery request input
  - [ ] Issue reset token for existing eligible account
  - [ ] Return generic response for existing and non-existing emails
  - [ ] Avoid existence leaks in response contract
- [ ] Add password reset confirm endpoint behavior
  - [ ] Accept reset token and new password input
  - [ ] Reject expired tokens
  - [ ] Reject replay/consumed tokens
  - [ ] Update password only on valid unused unexpired token
  - [ ] Mark token consumed after successful reset
  - [ ] Return generic/safe response shape per route contract
- [ ] Add session invalidation on successful reset
  - [ ] Identify current bearer/session invalidation mechanism in auth stack
  - [ ] Revoke existing user sessions/bearers after password change commits
  - [ ] Ensure post-reset stale bearer usage is denied
- [ ] Add backend and route-level tests
  - [ ] Cover token expiry
  - [ ] Cover single-use consumption and replay rejection
  - [ ] Cover request anti-enumeration behavior
  - [ ] Cover successful reset password mutation
  - [ ] Cover bearer/session revocation after reset

## Dev Notes
- Narrow-read scope: implement the full backend slice required by the direction in one story file, despite PM decomposition context. Sequence implementation in the order declared by PM notes: token/reset primitives first, request flow second, confirm flow third, session invalidation fourth, route-level verification last.
- flow.md: not provided by direction.
- api_spec.md: not provided by direction.
- Verbatim direction acceptance criteria:
  - [ ] Reset request/confirm endpoints use expiring single-use tokens with generic responses
  - [ ] Successful reset revokes existing sessions/bearers for that user
  - [ ] Tests verify token expiry, replay rejection, and anti-enumeration behavior
- Relevant context pointers:
  - [Source: context/project.md#Identity]
  - [Source: context/project.md#Stack]
  - [Source: context/project.md#Active constraints]
  - [Source: context/navigation.md#When working on auth or token lifecycle]
  - [Source: context/navigation.md#When working on replay defenses or session invalidation]
- Existing code anchors called out by context prelude:
  - `backend/app/routes/auth.py`
  - `backend/app/services/auth.py`
  - `backend/app/core/dependencies.py`
  - `backend/tests/test_auth.py`
  - `backend/tests/test_email_auth.py`
- Implementation constraints from context:
  - OAuth code-exchange behavior is already hardened; this story is only for email/password recovery.
  - Bearer compromise is high impact because the authenticated session reaches goals, payments, notifications, uploads, dashboard data, and chat-adjacent flows.
  - Password reset is an explicitly documented auth hardening gap.
  - CLI/mobile/web bearer persistence makes reset-triggered bearer revocation a first-order requirement.
- Review focus:
  - No account enumeration via request endpoint response semantics.
  - Expiry and single-use enforced server-side, not only by client behavior.
  - Reset success invalidates previously issued bearers across shared auth dependencies.
  - Tests prove expiry, replay rejection, anti-enumeration, and post-reset revocation.

## References
- Direction: `direction.md`
- PM decomposition context: `pm_result.child_stories`
- Backend auth routes: `backend/app/routes/auth.py`
- Backend auth services: `backend/app/services/auth.py`
- Auth dependencies: `backend/app/core/dependencies.py`
- Existing auth tests: `backend/tests/test_auth.py`
- Existing email auth tests: `backend/tests/test_email_auth.py`

## Dev Agent Record
- Status: Not started
- Agent: TBD
- Branch/PR: TBD
- Notes:
  - TBD

## Senior Developer Review
- Status: Pending
- Reviewer: TBD
- Notes:
  - Verify route contracts do not leak account existence.
  - Verify token replay is impossible after successful consumption.
  - Verify bearer revocation reaches all existing authenticated sessions for the user.

## Review Follow-ups
- None yet.
