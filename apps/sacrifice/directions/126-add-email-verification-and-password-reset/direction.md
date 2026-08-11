---
title: Add email verification and password reset
type: security
priority: p2
explore: true
created_at: '2026-08-10T15:34:38.734306+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Add email verification and password reset

## Why

Verified email ownership is the gatekeeper for password-based account recovery and prevents pre-registration account squatting.

## Acceptance Criteria

- [ ] Verification email is sent on registration and required before goal/payment mutations; password reset uses a time-limited signed token sent to the verified email.
