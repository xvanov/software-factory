---
title: Expose a goal-count endpoint for the authenticated user
type: feature
priority: p2
explore: false
created_at: '2026-08-09T07:30:00+00:00'
---

# Expose a goal-count endpoint for the authenticated user

## Why

The dashboard needs the caller's own goal total without paging the full goal
list. A dedicated count is cheap to serve and cheap to poll, and it gives the
factory a small, purely additive surface to exercise the chain end to end.

## Acceptance Criteria

- [ ] `GET /api/goals/count` returns the authenticated caller's own goal total as a JSON integer field
- [ ] The count reflects goals the caller creates: creating a goal increases it by exactly one
- [ ] An unauthenticated request is rejected rather than returning a count
