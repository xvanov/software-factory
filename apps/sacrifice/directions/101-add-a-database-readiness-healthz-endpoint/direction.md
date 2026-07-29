---
title: Add a database readiness healthz endpoint
type: feature
priority: p2
explore: false
created_at: '2026-07-21T02:17:39.144120+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Add a database readiness healthz endpoint

## Why

The existing health check does not verify the database is reachable, so a running app with a down/misconfigured DB still reports healthy and load balancers keep routing to it. A dedicated readiness endpoint that performs a trivial DB round-trip gives ops an honest 'ready to serve' signal and lets deploy/rollback gate on real DB connectivity. Small, backend-only, isolated.

## Acceptance Criteria

- [ ] GET /healthz/db returns 200 with body {"db": "ok"} when the database is reachable.
- [ ] GET /healthz/db returns 503 with body {"db": "unreachable"} when the DB round-trip fails.
- [ ] The check performs only a trivial read (e.g. SELECT 1), never a write, and requires no auth.
- [ ] A backend test covers both the healthy (200) and unreachable (503) paths.
