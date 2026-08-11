---
title: Harden token lifecycle and local storage
type: security
priority: p2
explore: true
created_at: '2026-08-10T15:34:38.966646+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Harden token lifecycle and local storage

## Why

Long-lived bearer tokens stored in easily accessible locations allow persistent account takeover if a device or browser is compromised.

## Acceptance Criteria

- [ ] Access tokens expire in minutes, refresh tokens rotate on use and are revocable, and CLI token is stored in the OS keychain with fallback encryption.
