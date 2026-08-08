---
title: Add verified-email lifecycle controls
type: security
priority: p2
explore: true
created_at: '2026-08-08T03:24:10.903551+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Add verified-email lifecycle controls

## Why

Mailbox proof is foundational to account trust and abuse resistance.

## Acceptance Criteria

- [ ] New email/password accounts require successful verification before sensitive operations
- [ ] Verification tokens are single-use, short-lived, and invalidated after use
- [ ] Tests cover unverified vs verified authorization behavior
