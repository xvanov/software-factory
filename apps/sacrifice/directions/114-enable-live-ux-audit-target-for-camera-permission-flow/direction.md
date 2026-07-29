---
title: Enable live UX audit target for camera permission flow
type: ux
priority: p2
explore: true
created_at: '2026-07-24T00:02:05.141309+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Enable live UX audit target for camera permission flow

## Why

The current runtime cannot observe the documented camera permission branch, leaving a core proof-submission UX path unaudited.

## Acceptance Criteria

- [ ] A scheduled UX audit can open the app, trigger Record proof, deny camera permission, and verify the expected error text plus Open settings and Cancel actions.
