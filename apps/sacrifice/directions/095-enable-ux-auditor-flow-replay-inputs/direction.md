---
title: Enable UX auditor flow replay inputs
type: ux
priority: p2
explore: true
created_at: '2026-07-19T18:01:03.156680+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Enable UX auditor flow replay inputs

## Why

The auditor cannot validate user-flow friction without the actual flow narratives and a runnable browser session.

## Acceptance Criteria

- [ ] UX auditor invocation includes extracted flow.md files in its input payload.
- [ ] UX auditor can access a live app URL in a browser-enabled sandbox and execute semantic Playwright locators against it.
- [ ] A scheduled run returns evidence from observed steps rather than reporting missing runtime inputs.
