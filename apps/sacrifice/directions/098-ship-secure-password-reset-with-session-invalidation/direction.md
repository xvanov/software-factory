---
title: Ship secure password reset with session invalidation
type: security
priority: p2
explore: true
created_at: '2026-07-20T09:06:10.401436+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Ship secure password reset with session invalidation

## Why

A robust reset channel is necessary to recover accounts safely and evict attackers after credential compromise.

## Acceptance Criteria

- [ ] Reset request/confirm endpoints use expiring single-use tokens with generic responses
- [ ] Successful reset revokes existing sessions/bearers for that user
- [ ] Tests verify token expiry, replay rejection, and anti-enumeration behavior
