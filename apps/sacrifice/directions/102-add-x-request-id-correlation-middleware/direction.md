---
title: Add X-Request-ID correlation middleware
type: feature
priority: p2
explore: false
created_at: '2026-07-22T23:34:18.650135+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Add X-Request-ID correlation middleware

## Why

Every HTTP response should carry a stable X-Request-ID so logs across middleware and handlers can be tied to a single request and a client can quote an id when reporting a failed request. Today there is no correlation id, so a request cannot be traced end-to-end and support/debugging is guesswork.

## Acceptance Criteria

- [ ] A GET to an existing endpoint (e.g. /healthz) returns a response containing an X-Request-ID header.
- [ ] When the request includes an X-Request-ID header, the response echoes that exact value.
- [ ] When the request omits X-Request-ID, the response contains a newly generated valid UUIDv4.
- [ ] The header is present on non-2xx responses as well (e.g. a 404).
- [ ] A backend test in tests/ covers echo, generation, and presence on a 404.
