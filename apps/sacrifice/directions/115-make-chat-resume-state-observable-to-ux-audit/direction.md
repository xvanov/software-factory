---
title: Make chat resume state observable to UX audit
type: ux
priority: p2
explore: true
created_at: '2026-07-24T00:02:05.303417+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Make chat resume state observable to UX audit

## Why

The audit cannot verify whether interrupted goal-creation chats resume correctly without a live persisted session.

## Acceptance Criteria

- [ ] A scheduled UX audit can leave the chat mid-flow, return later, and confirm the last assistant message and draft state are restored.
