# Story

## Title
Secure password reset and post-reset session revocation — narrow read

## Story
**As a** Sacrifice account holder recovering a compromised or inaccessible account
**I want** password reset behavior that does not reveal whether an account exists, uses a constrained reset token, and revokes previously active sessions after a successful reset
**so that** account recovery reduces compromise impact across all authenticated surfaces.

## Scope
Narrow-read backend story covering the full direction acceptance criteria as one auth-hardening slice: request-time non-enumeration, reset-token lifecycle semantics, and post-reset invalidation of active bearer sessions honored by the backend.

## Acceptance Criteria
- [ ] Password reset requests return non-enumerating responses
- [ ] Reset token is single-use, expiring, and invalidated on success
- [ ] All active sessions are revoked after password reset

### Testable Claims (EARS)
AC1.1: WHEN a password reset is requested, THE password reset request endpoint SHALL return a non-enumerating response.
AC2.1: WHEN a reset token is issued, THE reset-token lifecycle SHALL enforce single-use behavior.
AC2.2: WHEN a reset token is issued, THE reset-token lifecycle SHALL enforce expiration.
AC2.3: WHEN a password reset succeeds, THE system SHALL invalidate the reset token used for that success.
AC3.1: WHEN a password reset succeeds, THE authentication system SHALL revoke all active sessions.

## Tasks / Subtasks
- [ ] Audit current auth/password capabilities and identify insertion points in backend auth routes/services/models
- [ ] Define password reset request endpoint behavior with identical outward response for existing and non-existing accounts
- [ ] Implement reset-token persistence model and migration if current schema lacks reset-token storage/state
- [ ] Implement secure reset-token issuance path
- [ ] Implement reset-token verification path with expiration enforcement
- [ ] Implement reset-token consumption path with single-use invalidation on success
- [ ] Implement password update path gated by valid reset token
- [ ] Implement active-session revocation mechanism triggered by successful password reset
- [ ] Ensure auth dependencies reject bearer sessions issued before successful reset
- [ ] Add backend tests for non-enumerating request behavior
- [ ] Add backend tests for expired-token rejection
- [ ] Add backend tests for consumed-token reuse rejection
- [ ] Add backend tests proving successful reset revokes previously active bearer sessions across backend-authorized clients
- [ ] Update any fixtures/helpers required for reset-token and session-revocation coverage

## Dev Notes
### Direction Acceptance Criteria (verbatim)
- [ ] Password reset requests return non-enumerating responses
- [ ] Reset token is single-use, expiring, and invalidated on success
- [ ] All active sessions are revoked after password reset

### flow.md
(none)

### api_spec.md
(none)

### Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/navigation.md#When working on replay defenses or session invalidation]

### Implementation notes
- Existing project context explicitly calls out missing password reset flow in current auth surface; this story closes that gap without broadening into unrelated auth work.
- Existing auth constraint: OAuth flows already avoid returning raw access tokens via browser redirects; preserve current token-exchange posture while adding password reset behavior.
- Session revocation must cover backend-honored bearer sessions used by mobile, web, and CLI because project context states those clients persist bearer tokens locally and compromise impact spans shared authenticated routes.
- Minimize scope to observable backend behavior required by the direction; do not invent delivery-channel or UI requirements not present in direction.
- If current bearer validation is purely stateless, implementation must add the minimum server-side revocation check needed to make post-reset revocation observable at authorization time.
- If no explicit reset request/reset confirm contract exists, keep endpoint and payload changes tightly aligned to current auth route patterns and test for the stated outcomes rather than speculative API shape.

## References
- `backend/app/routes/auth.py`
- `backend/app/services/auth.py`
- `backend/app/core/dependencies.py`
- `backend/app/core/crypto.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_email_auth.py`
- `frontend/services/auth.ts`
- `backend/cli/client.py`

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
