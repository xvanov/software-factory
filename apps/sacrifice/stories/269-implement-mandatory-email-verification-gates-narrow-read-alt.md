# Story

## Title
Implement mandatory email verification gates — narrow read

## Slug
implement-mandatory-email-verification-gates-narrow-read-alt

## Scope
backend

## Summary
Implement the narrowest backend slice that satisfies the direction by introducing mandatory email-verification support for email/password accounts, enforcing blocking through one shared sensitive-action auth dependency, and covering token lifecycle constraints needed by that gate.

# Acceptance Criteria

- [ ] New email/password accounts are created in an unverified state
- [ ] Sensitive actions are blocked until verification is completed
- [ ] Verification tokens are single-use, expiring, and resend is rate-limited

### Testable Claims (EARS)
AC1.1: WHEN a new email/password account is created, THE system SHALL create the account in an unverified state
AC2.1: WHEN a user attempts a sensitive action, GIVEN the account is not verified, THE system SHALL block the action until verification is completed
AC3.1: WHEN the system issues or processes a verification token, THE verification token mechanism SHALL enforce single-use behavior
AC3.2: WHEN the system issues or processes a verification token, THE verification token mechanism SHALL enforce expiry
AC3.3: WHEN a user requests resend of verification, THE system SHALL rate-limit resend requests

# Tasks / Subtasks

- [ ] Confirm existing email/password registration persistence path and auth dependency entrypoints
- [ ] Add persisted verification state for email/password accounts created by signup flow
- [ ] Ensure signup path defaults new email/password accounts to unverified
- [ ] Add verification-token persistence/model support with single-use and expiry fields
- [ ] Add token issuance service logic for email verification
- [ ] Add token redemption service logic that marks token used and account verified
- [ ] Add resend path enforcement with rate limiting
- [ ] Add one shared sensitive-action auth dependency or equivalent common gate for unverified-account blocking
- [ ] Wire at least one existing sensitive backend path through the shared verification gate
- [ ] Add backend tests covering unverified signup state
- [ ] Add backend tests covering token single-use behavior
- [ ] Add backend tests covering token expiry behavior
- [ ] Add backend tests covering resend rate limiting
- [ ] Add backend tests covering blocked sensitive action before verification
- [ ] Add backend tests covering allowed sensitive action after verification
- [ ] Keep scope narrow: shared enforcement path only, not route-by-route expansion across all authenticated surfaces

# Dev Notes

## Scope interpretation
Narrow read for this assigned story: prepare one backend story that captures the smallest shippable implementation aligned to the direction and PM sequencing notes. This story is intentionally centered on one shared sensitive-action enforcement path, while still including the prerequisite verification-state and token-lifecycle work required to make that gate real and testable.

## flow.md
[flow.md: none]

## api_spec.md
[api_spec.md: none]

## Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Stack]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/navigation.md#When working on replay defenses or session invalidation]

## Implementation notes
- Email/password auth already exists; extend that path rather than introducing a parallel account type.
- OAuth browser/mobile flows already use one-time `auth_code` exchange; this story is about email/password account verification, not changing OAuth redirect semantics.
- Sensitive-action enforcement should land in one shared backend auth dependency or equivalent common gate so downstream stories can expand coverage without redefining verification semantics.
- CLI/local bearer persistence and mobile/web local bearer persistence increase the security impact of leaving unverified accounts unrestricted; blocking should happen server-side.
- Existing known auth hardening gaps include no email verification flow, no password reset flow, and no visible rate limiting on login/register endpoints; do not broaden into those unrelated gaps except where resend limiting is explicitly required by this direction.
- Because no `flow.md` or `api_spec.md` was provided, downstream test planning should derive behavior only from the direction ACs, PM decomposition, and referenced context files.

## Direction acceptance criteria (verbatim)
- [ ] New email/password accounts are created in an unverified state
- [ ] Sensitive actions are blocked until verification is completed
- [ ] Verification tokens are single-use, expiring, and resend is rate-limited

# References

- PM tracker: `D093 implement mandatory email verification gates`
- Child-story decomposition context:
  - `D093 add unverified email state on email/password signup`
  - `D093 issue expiring single-use email verification tokens`
  - `D093 redeem verification token and mark account verified`
  - `D093 rate-limit resend verification requests`
  - `D093 gate one shared sensitive-action auth dependency`
  - `D093 expose frontend handling for unverified-action blocks`
- Canonical docs:
  - `context/project.md`
  - `context/navigation.md`

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
