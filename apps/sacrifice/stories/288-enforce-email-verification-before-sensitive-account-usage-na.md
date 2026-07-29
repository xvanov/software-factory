# Story

## Title
Enforce email verification before sensitive account usage — narrow read

## Slug
`enforce-email-verification-before-sensitive-account-usage-na`

## Scope
`backend`

## Summary
Implement the narrow backend slice for D097 by establishing signed, single-use, expiring email verification token issuance/redeem behavior for new email/password accounts, and prove one verified-vs-unverified authorization path in tests without broad route rollout.

# Acceptance Criteria

- [ ] New email/password accounts remain restricted until verification token is redeemed
- [ ] Verification tokens are single-use, expiring, and cryptographically signed
- [ ] Tests cover verified vs unverified authorization paths

### Testable Claims (EARS)
AC1.1: WHEN a new email/password account is created, THE account SHALL remain restricted until the verification token is redeemed
AC2.1: WHEN a verification token is issued, THE token SHALL be cryptographically signed
AC2.2: WHEN a verification token is issued, THE token SHALL be expiring
AC2.3: WHEN a verification token is redeemed successfully, THE token SHALL become single-use
AC2.4: WHEN redemption is attempted with a previously redeemed verification token, THE verification flow SHALL reject the token
AC2.5: WHEN redemption is attempted with an expired verification token, THE verification flow SHALL reject the token
AC3.1: WHEN authorization is attempted by an unverified account on the selected sensitive path, THE system SHALL exhibit the unverified authorization outcome covered by tests
AC3.2: WHEN authorization is attempted by a verified account on the selected sensitive path, THE system SHALL exhibit the verified authorization outcome covered by tests

# Tasks / Subtasks

- [ ] Confirm narrow-read scope boundary against PM decomposition
- [ ] Add persistent verification state for new email/password accounts
- [ ] Default new email/password accounts to unverified
- [ ] Exclude existing OAuth behavior from regression in this slice
- [ ] Implement signed verification token issuance
- [ ] Implement token expiry validation
- [ ] Implement single-use redemption enforcement
- [ ] Mark account verified only on successful redemption
- [ ] Prevent repeated successful redemption of the same token
- [ ] Select one sensitive authorization path for proof of restriction
- [ ] Wire verified-email check into the selected path or shared dependency
- [ ] Add backend tests for token issue/redeem lifecycle
- [ ] Add backend tests for expired token rejection
- [ ] Add backend tests for single-use rejection after redemption
- [ ] Add backend tests for verified vs unverified authorization on the selected path
- [ ] Verify unchanged behavior for already verified email/password accounts on the selected path
- [ ] Verify story does not broaden enforcement to remaining sensitive routes

# Dev Notes

## Scope boundary
- Narrow read for this assigned story: deliver the foundational verification-token lifecycle and one representative authorization proof path only.
- Do not expand enforcement to all sensitive routes in this story.
- Do not invent productized email delivery UX requirements absent from direction.

## flow.md
(none)

## api_spec.md
(none)

## Direction acceptance criteria (verbatim)
- [ ] New email/password accounts remain restricted until verification token is redeemed
- [ ] Verification tokens are single-use, expiring, and cryptographically signed
- [ ] Tests cover verified vs unverified authorization paths

## Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/navigation.md#When working on replay defenses or session invalidation]
- [Source: context/current-state.md#Authentication and Authorization]
- [Source: context/current-state.md#Security Posture]
- [Source: context/modules/auth.md#Email/password authentication]
- [Source: context/modules/auth.md#OAuth and token exchange]
- [Source: context/modules/security.md#Auth risks and hardening gaps]
- [Source: context/modules/backend.md#FastAPI app structure]

## Implementation notes
- Direction is explicitly limited to new email/password accounts.
- Current project context names bearer compromise as high impact across goals, payments, notifications, uploads, dashboard data, and chat-adjacent flows; use that to justify picking one representative sensitive path, preferably through shared auth dependency if feasible.
- OAuth browser/mobile flows already use one-time auth_code exchange; do not conflate that mechanism with email verification tokens.
- Local bearer persistence in frontend and CLI makes verified-email state a security control, not just UI metadata.
- If current data model lacks an email-verified flag and/or verification-token persistence needed for single-use semantics, add the minimum backend state required for this narrow slice.
- Cryptographic signing, expiry validation, and single-use invalidation must be observable in backend tests.
- Keep error/response assertions aligned with existing auth conventions in backend routes/tests; do not introduce undocumented response shapes unless implementation requires them and tests pin them.
- If context/current-state.md or module docs use different naming than code, code truth wins for exact identifiers; preserve story scope.

# References

- `backend/app/routes/auth.py`
- `backend/app/services/auth.py`
- `backend/app/core/dependencies.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_email_auth.py`
- `backend/app/core/crypto.py`

# Dev Agent Record

## Agent Model Used
- TBD

## Debug Log References
- TBD

## Completion Notes
- TBD

## File List
- TBD

# Senior Developer Review

- TBD

# Review Follow-ups

- TBD
