---
title: Protect CLI bearer token with OS keychain
type: security
priority: p2
explore: true
created_at: '2026-08-10T15:34:39.533791+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Protect CLI bearer token with OS keychain

## Why

A plaintext token on disk is trivially exfiltrated by local malware or shared-workstation attackers.

## Acceptance Criteria

- [ ] CLI token is stored in the OS keychain with an encrypted fallback, and the config file contains no plaintext credentials.
