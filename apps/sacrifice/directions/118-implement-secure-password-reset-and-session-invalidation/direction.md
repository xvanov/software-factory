---
title: Implement secure password reset and session invalidation
type: security
priority: p2
explore: true
created_at: '2026-08-08T03:24:11.133084+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Implement secure password reset and session invalidation

## Why

Credential recovery is required to contain compromise and restore user control.

## Acceptance Criteria

- [ ] Reset request and completion endpoints use anti-enumeration responses and throttling
- [ ] Reset tokens are signed, short-lived, single-use, and bound to the intended account
- [ ] Successful password reset revokes active sessions/tokens for that user
