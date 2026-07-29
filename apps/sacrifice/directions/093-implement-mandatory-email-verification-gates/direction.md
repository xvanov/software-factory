---
title: Implement mandatory email verification gates
type: security
priority: p2
explore: true
created_at: '2026-07-19T13:58:13.079659+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Implement mandatory email verification gates

## Why

Unverified identities reduce trust and increase abuse/fraud surface.

## Acceptance Criteria

- [ ] New email/password accounts are created in an unverified state
- [ ] Sensitive actions are blocked until verification is completed
- [ ] Verification tokens are single-use, expiring, and resend is rate-limited
