---
title: 'Add sign-in test coverage: Playwright e2e against the deployed instance plus
  unit'
type: test
priority: p2
explore: true
created_at: '2026-07-23T17:34:06.666715+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Add sign-in test coverage: Playwright e2e against the deployed instance plus unit

## Why

Sign-in regressions have shipped undetected and blocked deploys. Add automated coverage: a Playwright e2e that drives the sign-in flow against the deployed instance, plus local unit coverage of the auth_code callback + exchange. Builds on existing frontend/e2e/*.spec.ts and frontend/__tests__/services/auth.test.ts. Note gates.e2e_harness_ready is currently false.

## Acceptance Criteria

- [ ] A Playwright e2e spec exercises Google and GitHub sign-in and asserts an authenticated end state (mock provider or documented test creds as needed).
- [ ] Unit tests cover handleRedirectCallback for auth_code, access_token, and error params, and exchangeCode success + failure.
- [ ] The e2e target is runnable (gates.e2e_harness_ready wired true or a documented runner) and passes against the deployed base URL.
- [ ] The sign-in unit tests run in CI on changes to frontend/services/auth.ts or frontend/hooks/useAuth.tsx.
