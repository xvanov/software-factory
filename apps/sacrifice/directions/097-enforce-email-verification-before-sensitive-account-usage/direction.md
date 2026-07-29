---
title: Enforce email verification before sensitive account usage
type: security
priority: p2
explore: true
created_at: '2026-07-20T09:06:10.277685+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Enforce email verification before sensitive account usage

## Why

Mailbox proof reduces fraudulent account creation and strengthens identity assurance.

## Acceptance Criteria

- [ ] New email/password accounts remain restricted until verification token is redeemed
- [ ] Verification tokens are single-use, expiring, and cryptographically signed
- [ ] Tests cover verified vs unverified authorization paths
