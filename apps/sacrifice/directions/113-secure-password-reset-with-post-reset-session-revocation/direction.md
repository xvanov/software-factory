---
title: Secure password reset with post-reset session revocation
type: backend
priority: p2
explore: true
created_at: '2026-07-23T22:32:57.029048+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Secure password reset with post-reset session revocation

## Why

The live app supports email/password auth (POST /api/auth/email/register, /api/auth/email/login) and OAuth, but has NO password-reset path — a user who forgets their password is locked out. Add a secure reset flow. Session model: each user has auth_session_id (backend/app/services/auth.py); JWTs embed it, so ROTATING auth_session_id revokes all existing sessions. There is NO email-sending infra in the app today, so token DELIVERY (email) is explicitly OUT OF SCOPE here (a follow-up once email infra lands) — model the reset TOKEN on the existing signed csrf_token pattern (a short-TTL, single-use, purpose-scoped JWT), and exercise the request->confirm flow in tests directly. Do NOT return the raw reset token in the request response (that would defeat the point); tests mint a token via the service.

## Acceptance Criteria

- [ ] POST /api/auth/password/reset/request returns 202 for BOTH a known and an unknown email (no user enumeration), and never returns the reset token in the response body.
- [ ] A valid single-use reset token lets POST /api/auth/password/reset/confirm set a new password; the old password no longer authenticates and the new one does.
- [ ] Confirming a reset ROTATES auth_session_id so a JWT/session issued before the reset is rejected afterward (session revocation).
- [ ] A reset token is single-use (a second confirm with the same token is 400), expires (<=30m), and is purpose-scoped (a csrf/access token cannot be used as a reset token).
- [ ] New password must satisfy the same policy as registration; a weak password is rejected 400/422.
- [ ] Backend unit tests cover: happy path, unknown-email non-enumeration, reused token, expired token, wrong-purpose token, weak password, and post-reset session revocation. Email DELIVERY is explicitly out of scope (no email infra) and noted as a follow-up.
