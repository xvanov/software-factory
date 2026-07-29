---
title: '[BUG] Login/register return 400 on mobile (Expo Go) but work on web'
type: ''
priority: p2
explore: false
created_at: '2026-07-18T13:38:14.090326+00:00'
source_issue: 229
---

## Why
Logging in (and registering) from the app in Expo Go fails with HTTP 400 "Bad request." The web app works fine.

## Diagnosis (already root-caused)
The 400 is injected by **Cloudflare at the edge, before the backend** — the backend never receives the request (confirmed: direct-to-origin POST returns a normal 401, and no POST appears in backend logs). It is scoped to POSTs on the auth paths (`/api/auth/email/login`, `/api/auth/email/register`) via `sacrifice.rentus.homes`; benign POSTs elsewhere reach the origin (405), and the rental app on the same zone is unaffected.

Root cause: a **Cloudflare WAF managed rule on the rentus.homes zone** blocking POSTs to authentication endpoints.

## Acceptance criteria
- [ ] POST `/api/auth/email/login` and `/api/auth/email/register` succeed through `sacrifice.rentus.homes` (reach the origin; return 200/401 by credentials, never a CF 400).
- [ ] The fix is scoped to `sacrifice.rentus.homes` and does NOT weaken WAF protection on rentus.homes / app.rentus.homes.

## NOTE for triage
This is **Cloudflare zone configuration, not application code** — a WAF exception/skip rule scoped to sacrifice.rentus.homes auth paths. The code-editing pipeline cannot fix it; it needs a Cloudflare dashboard/API change. Flag as infra rather than attempting a code change.
