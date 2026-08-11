---
title: Add session invalidation and logout-all
type: security
priority: p2
explore: true
created_at: '2026-08-10T15:34:39.156088+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Add session invalidation and logout-all

## Why

Password changes and security events are ineffective if previously issued tokens remain valid.

## Acceptance Criteria

- [ ] A logout-all endpoint revokes all refresh tokens for the user, and password change triggers automatic revocation of all existing sessions.
