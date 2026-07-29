---
title: Add secure password reset and session revocation on reset
type: security
priority: p2
explore: true
created_at: '2026-07-19T13:58:13.189082+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Add secure password reset and session revocation on reset

## Why

Without recovery and forced rotation, compromised credentials remain exploitable for longer.

## Acceptance Criteria

- [ ] Forgot-password issues expiring single-use reset tokens without disclosing account existence
- [ ] Reset endpoint enforces token validity, complexity checks, and attempt throttling
- [ ] Successful reset revokes prior active sessions/tokens
