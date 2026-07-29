# Story

## Title
Mandatory email verification before full session issuance — narrow read

## Slug
`mandatory-email-verification-before-full-session-issua-alt-a`

## Scope
`backend`

## Summary
Implement the narrow backend slice for mandatory email verification before full session issuance. This story prepares a developer-ready sequence that covers restricted email/password account state, single-use expiring verification token lifecycle, verification consumption, and protected-route enforcement without introducing frontend UX scope.

# Acceptance Criteria

- [x] New email/password accounts remain restricted until verification
- [x] Verification token is single-use, time-bounded, and auditable
- [x] Protected routes reject unverified sessions with clear error semantics

### Testable Claims (EARS)
AC1.1: WHEN a new email/password account is created, THE auth system SHALL keep that account in a restricted state until verification
AC2.1: WHEN a verification token is issued or redeemed, THE verification-token component SHALL enforce single-use behavior
AC2.2: WHEN a verification token exists, THE verification-token component SHALL enforce a time-bounded validity window
AC2.3: WHEN verification-token lifecycle actions occur, THE system SHALL record auditable evidence of those actions
AC3.1: WHEN a protected route receives a request from an unverified session, THE protected-route auth dependency SHALL reject the request with clear error semantics

# Tasks / Subtasks

- [ ] Define durable verification state for email/password users
  - [ ] Identify persistence location in auth/user model layer
  - [ ] Add migration for verification-state fields if schema changes are required
  - [ ] Add backend tests proving new email/password accounts start unverified/restricted
- [ ] Restrict registration-issued sessions for unverified email/password accounts
  - [ ] Update registration flow to issue restricted session semantics
  - [ ] Preserve existing non-email/password auth behavior unless explicitly impacted by scope
  - [ ] Add route/service tests for restricted registration result
- [ ] Add verification token lifecycle primitives
  - [ ] Create token model/storage with single-use state
  - [ ] Add expiry handling for issued tokens
  - [ ] Add auditable fields/events for issuance and consumption
  - [ ] Add tests for issuance, expiry, and replay rejection
- [ ] Add verification consume flow
  - [ ] Accept valid token and mark account verified
  - [ ] Mark token consumed on successful verification
  - [ ] Reject consumed token reuse
  - [ ] Reject expired token redemption
  - [ ] Add tests for success and failure semantics
- [ ] Enforce verified-only access on protected routes
  - [ ] Add shared dependency or equivalent auth gate for verified-session requirement
  - [ ] Apply gate to protected routes in scope of existing auth dependency pattern
  - [ ] Return clear backend error semantics for unverified sessions
  - [ ] Add targeted protected-route coverage
- [ ] Keep implementation narrow
  - [ ] No frontend UX/copy changes in this story
  - [ ] No password-reset/email-change scope unless required by existing auth path wiring
  - [ ] No OAuth behavior changes unless existing shared auth code makes them unavoidable

# Dev Notes

## Scope read
Narrow read: implement only the server-observable security behavior explicitly required by the direction. Do not expand into frontend UX, copy, resend-email flows, admin tooling, or broader identity lifecycle redesign.

## flow.md
(none)

## api_spec.md
(none)

## Direction acceptance criteria (verbatim)
- [x] New email/password accounts remain restricted until verification
- [x] Verification token is single-use, time-bounded, and auditable
- [x] Protected routes reject unverified sessions with clear error semantics

## Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Stack]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/navigation.md#When working on replay defenses or session invalidation]

## Existing-code pointers called out by current context
- `backend/app/routes/auth.py`
- `backend/app/services/auth.py`
- `backend/app/core/dependencies.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_email_auth.py`
- `frontend/services/auth.ts` (read only to confirm bearer persistence assumptions; no frontend implementation in this story)
- `backend/cli/client.py` (read only to confirm bearer persistence assumptions; no CLI implementation in this story)

## Implementation notes
- Registration for email/password auth currently has an open hardening gap: no email verification flow is present. This story closes that gap only as far as mandatory verification before full session trust.
- OAuth browser/mobile flow already uses one-time `auth_code` exchange and should not be broadened by this story unless shared auth/session primitives force a no-op-compatible adjustment.
- Bearer compromise is high impact across goals, payments, notifications, uploads, dashboard data, and chat-adjacent flows. Treat any session-state distinction as authorization-significant, not cosmetic.
- Prefer shared auth dependency enforcement over route-by-route bespoke checks so protected-route behavior remains consistent.
- “Clear error semantics” must be implemented as stable backend-observable response behavior and covered by tests. Do not rely on undocumented implicit exceptions.
- “Auditable” requires persisted or otherwise inspectable evidence tied to token issuance/consumption. Logging-only behavior is insufficient unless tests can deterministically assert it and the implementation is durable enough for review.
- Keep tests authoritative: add or update backend tests first for restricted registration, token expiry/replay, verification success, and protected-route rejection.

## Suggested sequencing aligned to PM decomposition
1. Add user verification state and restricted-session tests.
2. Register email/password accounts into restricted state.
3. Add single-use expiring verification token issuance with audit fields.
4. Consume token to verify account and mark token used.
5. Gate protected routes for unverified sessions.

## Out-of-scope guardrails
- No frontend screens, banners, or copy
- No resend-verification product flow unless needed as a minimal helper for tests
- No password reset redesign
- No email provider integration expansion beyond what is minimally needed for backend verification token behavior
- No broad rework of existing auth architecture

# References

- `context/project.md`
- `context/navigation.md`
- `backend/app/routes/auth.py`
- `backend/app/services/auth.py`
- `backend/app/core/dependencies.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_email_auth.py`
- `frontend/services/auth.ts`
- `backend/cli/client.py`

# Dev Agent Record

- Agent: openhands (Amelia)
- Status: Complete
- Notes: All acceptance criteria satisfied with production code that already existed in the codebase. No production code changes were needed — the verification infrastructure (User.email_verified, VerificationToken model, verification service, routes, and require_verified_email dependency) was already implemented. Added comprehensive test coverage (24 tests) in `backend/tests/test_verification.py` proving every EARS claim:
  - AC1.1: `test_email_register_creates_unverified_account`, `test_email_login_issues_token_even_when_unverified`, `test_email_register_persists_unverified_state`
  - AC2.1: `test_verification_token_cannot_be_reused`, `test_verification_token_consumed_flag_is_persisted`, `test_nonexistent_token_is_rejected`
  - AC2.2: `test_expired_verification_token_is_rejected`, `test_valid_token_within_window_is_accepted`, `test_verification_token_has_future_expiry`
  - AC2.3: `test_verification_token_issuance_is_auditable`, `test_verification_token_consumption_is_auditable`, `test_user_verified_at_is_recorded`
  - AC3.1: `test_unverified_user_cannot_access_goals`, `test_unverified_user_cannot_access_dashboard`, `test_unverified_user_cannot_access_notifications`, `test_unverified_user_cannot_access_payment_config`, `test_verified_user_can_access_protected_routes`, `test_unverified_user_can_access_auth_me`, `test_unverified_user_can_refresh_token`, `test_unverified_user_can_logout`, `test_oauth_accounts_bypass_verification_gate`
  - Edge cases: `test_resend_verification_for_already_verified_returns_409`, `test_resend_verification_returns_existing_pending_token`, `test_verify_endpoint_does_not_require_auth`

File List:
  - `backend/tests/test_verification.py` (new)

# Senior Developer Review

- Reviewer: _TBD_
- Status: Pending
- Notes: _TBD_

# Review Follow-ups

- _None yet_
