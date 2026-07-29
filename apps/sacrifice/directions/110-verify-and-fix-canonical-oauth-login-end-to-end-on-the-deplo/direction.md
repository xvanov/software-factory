---
title: Verify and fix canonical OAuth login end-to-end on the deployed web app
type: bug
priority: p1
explore: true
created_at: '2026-07-23T17:34:06.665034+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Verify and fix canonical OAuth login end-to-end on the deployed web app

## Why

The canonical code (one-time auth_code exchange + OAuth CSRF/state cookie set at login, commit 030b758) must let a real user complete Google AND GitHub sign-in in a desktop browser on the deployed instance and end authenticated. Deployment is currently pinned to an older base because in-browser login did not complete end-to-end. The frontend path exists (frontend/services/auth.ts handleRedirectCallback -> exchangeCode; frontend/hooks/useAuth.tsx), so the gap is likely deploy staleness or an origin / redirect-URI / cookie mismatch (OAuth redirect URIs currently target k-911-x17.porgy-boga.ts.net). Verify on the deployed origin and fix whatever prevents completion without regressing the CSRF hardening.

## Acceptance Criteria

- [ ] Clicking 'Sign in with Google' on the deployed web app completes OAuth and ends authenticated (token stored, user loaded, no redirect-error banner).
- [ ] Clicking 'Sign in with GitHub' on the deployed web app completes OAuth and ends authenticated.
- [ ] After the provider redirect, the web client POSTs /api/auth/exchange with the ?auth_code= from the callback URL and stores the returned access_token.
- [ ] The OAuth state/CSRF cookie set at /api/auth/<provider>/login is present and honored on the callback on the deployed origin.
- [ ] A reproducible check (e2e spec or documented manual steps) demonstrates a full sign-in against the deployed instance.
