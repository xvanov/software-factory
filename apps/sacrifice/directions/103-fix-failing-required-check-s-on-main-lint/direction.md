---
title: 'Fix failing required check(s) on main: lint'
type: bug
priority: p2
explore: true
created_at: '2026-07-23T05:02:04.513722+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Fix failing required check(s) on main: lint

## Why

Post-merge CI-health monitor: the required check(s) lint are failing on sacrifice's main branch AFTER merge (the pre-merge required-check gate is unchanged and remains the primary defense; this is the post-merge safety net). Fix the exact failure below so main goes green again.

=== lint ===
run 29981031391 is still in progress; logs will be available when it is complete

<!-- ci-health-signature: f09363057304ede5ff94be25f8e64bb0f90c78a556faf708b0679b7c8a215bda -->

## Acceptance Criteria

- [ ] lint passes on sacrifice's main branch
