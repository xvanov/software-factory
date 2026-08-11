---
title: Improve secrets encryption key management
type: security
priority: p2
explore: true
created_at: '2026-08-10T15:34:39.344941+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Improve secrets encryption key management

## Why

A single static key guarding all stored secrets creates a broad at-rest exposure if the key is compromised.

## Acceptance Criteria

- [ ] Encryption key is sourced from a KMS/secret manager and supports rotation; stored ciphertexts include a key version identifier.
