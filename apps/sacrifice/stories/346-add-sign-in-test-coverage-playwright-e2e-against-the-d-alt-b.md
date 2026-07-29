# Story

## Title
Add sign-in test coverage: Playwright e2e against the deployed instance plus unit — broad read

## Scope
frontend

## Summary
Deliver the full sign-in coverage outcome as one broad frontend story: add regression unit coverage for auth redirect/exchange behavior, make the deployed Playwright auth runner executable, add provider-path e2e coverage for Google and GitHub authenticated end state, and ensure sign-in unit coverage runs in CI when auth frontend files change.

# Acceptance Criteria

- [ ] A Playwright e2e spec exercises Google and GitHub sign-in and asserts an authenticated end state (mock provider or documented test creds as needed).
- [ ] Unit tests cover handleRedirectCallback for auth_code, access_token, and error params, and exchangeCode success + failure.
- [ ] The e2e target is runnable (gates.e2e_harness_ready wired true or a documented runner) and passes against the deployed base URL.
- [ ] The sign-in unit tests run in CI on changes to frontend/services/auth.ts or frontend/hooks/useAuth.tsx.

### Testable Claims (EARS)
AC1.1: WHEN the sign-in Playwright suite runs, THE e2e spec SHALL exercise Google sign-in.
AC1.2: WHEN the sign-in Playwright suite runs, THE e2e spec SHALL exercise GitHub sign-in.
AC1.3: WHEN each provider sign-in flow completes, THE system SHALL present an authenticated end state.
AC1.4: WHEN provider execution requires environment-specific handling, THE test path SHALL use either a mock provider or documented test credentials as needed.
AC2.1: WHEN handleRedirectCallback receives an auth_code parameter, THE unit test suite SHALL cover that branch.
AC2.2: WHEN handleRedirectCallback receives an access_token parameter, THE unit test suite SHALL cover that branch.
AC2.3: WHEN handleRedirectCallback receives an error parameter, THE unit test suite SHALL cover that branch.
AC2.4: WHEN exchangeCode succeeds, THE unit test suite SHALL cover the success path.
AC2.5: WHEN exchangeCode fails, THE unit test suite SHALL cover the failure path.
AC3.1: WHEN the deployed sign-in e2e target is invoked, THE test harness SHALL be runnable.
AC3.2: WHEN the e2e harness readiness path is implemented, THE system SHALL either wire gates.e2e_harness_ready true or provide a documented runner.
AC3.3: WHEN the runnable e2e target executes against the deployed base URL, THE target SHALL pass.
AC4.1: WHEN frontend/services/auth.ts changes, THE CI system SHALL run the sign-in unit tests.
AC4.2: WHEN frontend/hooks/useAuth.tsx changes, THE CI system SHALL run the sign-in unit tests.

# Tasks / Subtasks

- [ ] Inspect existing auth/unit/e2e surfaces
  - [ ] Review `frontend/__tests__/services/auth.test.ts`
  - [ ] Review `frontend/services/auth.ts`
  - [ ] Review `frontend/hooks/useAuth.tsx`
  - [ ] Review existing Playwright specs under `frontend/e2e/*.spec.ts`
  - [ ] Identify current CI workflow entrypoints for frontend test execution
- [ ] Add unit coverage for redirect callback branches
  - [ ] Cover `handleRedirectCallback` with `auth_code` params
  - [ ] Cover `handleRedirectCallback` with `access_token` params
  - [ ] Cover `handleRedirectCallback` with `error` params
  - [ ] Assert branch-specific observable outcomes
- [ ] Add unit coverage for code exchange behavior
  - [ ] Cover `exchangeCode` success path
  - [ ] Cover `exchangeCode` failure path
  - [ ] Reuse existing test harness/mocking patterns where present
- [ ] Make deployed Playwright auth runner executable
  - [ ] Establish deployed base URL configuration path
  - [ ] Wire `gates.e2e_harness_ready` true or document the runner path in-repo
  - [ ] Ensure the auth e2e command is reproducible by downstream agents/CI
- [ ] Add provider e2e coverage
  - [ ] Add Google sign-in Playwright coverage
  - [ ] Add GitHub sign-in Playwright coverage
  - [ ] Assert authenticated end state after each provider flow
  - [ ] Use mock provider or documented test credentials as needed
- [ ] Wire CI protection for sign-in unit coverage
  - [ ] Ensure sign-in unit tests run when `frontend/services/auth.ts` changes
  - [ ] Ensure sign-in unit tests run when `frontend/hooks/useAuth.tsx` changes
  - [ ] Keep workflow scope limited to requested auth file triggers
- [ ] Validate end-to-end completion
  - [ ] Run local unit tests for auth redirect/exchange coverage
  - [ ] Run the deployed Playwright target against the deployed base URL
  - [ ] Record exact commands/paths in story implementation notes

# Dev Notes

## Flow Embed
(none)

## API Spec Embed
(none)

## Context Pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Stack]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/navigation.md#When working on replay defenses or session invalidation]
- [Source: context/navigation.md#When working on mobile or web login UX]

## Direction Acceptance Criteria (verbatim embed)
- [ ] A Playwright e2e spec exercises Google and GitHub sign-in and asserts an authenticated end state (mock provider or documented test creds as needed).
- [ ] Unit tests cover handleRedirectCallback for auth_code, access_token, and error params, and exchangeCode success + failure.
- [ ] The e2e target is runnable (gates.e2e_harness_ready wired true or a documented runner) and passes against the deployed base URL.
- [ ] The sign-in unit tests run in CI on changes to frontend/services/auth.ts or frontend/hooks/useAuth.tsx.

## Implementation Notes
- Broad-read scope intentionally combines all PM-decomposed slices into one story file because this assignment targets the direction-level outcome rather than an individual child story slug.
- Preserve the current auth architecture constraint: OAuth browser/mobile flows redirect with a one-time `auth_code`; they do not redirect raw access tokens back to the frontend. Unit coverage for `access_token` params is still required because the direction explicitly requires that branch.
- Prefer extending existing tests before creating parallel test files unless the existing harness structure blocks clear separation.
- The Playwright path must target the deployed instance, not only local dev services.
- `gates.e2e_harness_ready` is currently false per direction/project context; this story is not complete until the runner path is made real.
- The provider-flow implementation may choose mocked providers or documented test credentials; whichever path is selected must still prove authenticated end state.
- CI enforcement must be scoped to the requested file-change triggers and must execute the sign-in unit coverage rather than a purely unrelated frontend suite.

## Expected File Touch Points
- `frontend/__tests__/services/auth.test.ts`
- `frontend/services/auth.ts`
- `frontend/hooks/useAuth.tsx`
- `frontend/e2e/*.spec.ts`
- CI workflow/config files that govern frontend test execution
- Any gate/config file needed to make `gates.e2e_harness_ready` true or to document a canonical runner path in-repo

# References

- `frontend/__tests__/services/auth.test.ts`
- `frontend/services/auth.ts`
- `frontend/hooks/useAuth.tsx`
- `frontend/e2e/*.spec.ts`
- `context/project.md`
- `context/navigation.md`
- Direction: `direction.md`

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
