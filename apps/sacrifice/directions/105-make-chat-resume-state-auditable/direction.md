---
title: Make chat resume state auditable
type: ux
priority: p2
explore: true
created_at: '2026-07-23T06:00:39.122580+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Make chat resume state auditable

## Why

The documented mid-flow return experience cannot currently be observed in the scheduled UX audit runtime.

## Acceptance Criteria

- [ ] Scheduled UX audit can leave the chat flow, return later, and verify the session resumes from the last assistant message with objective evidence.
