---
title: Mandatory email verification before full session issuance
type: security
priority: p2
explore: true
created_at: '2026-07-23T09:06:31.248766+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Mandatory email verification before full session issuance

## Why

Unverified accounts undermine identity trust and recovery security.

## Acceptance Criteria

- [ ] New email/password accounts remain restricted until verification
- [ ] Verification token is single-use, time-bounded, and auditable
- [ ] Protected routes reject unverified sessions with clear error semantics
