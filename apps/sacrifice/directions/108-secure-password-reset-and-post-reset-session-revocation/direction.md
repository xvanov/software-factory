---
title: Secure password reset and post-reset session revocation
type: security
priority: p2
explore: true
created_at: '2026-07-23T09:06:31.440265+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Secure password reset and post-reset session revocation

## Why

Recovery controls are required to contain account compromise impact.

## Acceptance Criteria

- [ ] Password reset requests return non-enumerating responses
- [ ] Reset token is single-use, expiring, and invalidated on success
- [ ] All active sessions are revoked after password reset
