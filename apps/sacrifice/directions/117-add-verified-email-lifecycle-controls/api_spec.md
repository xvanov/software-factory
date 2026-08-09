# API contract — Add verified-email lifecycle controls

> Authored by the `contract` persona from the direction's acceptance
> criteria and the app's REAL route table. This file is the shared
> contract: the implementer builds to it and the independent acceptance
> oracle grades against it. Paths here are exact.

## Endpoints

### `POST /api/auth/email/register` _(existing)_

Register a new email/password account. The user record must be created in an unverified state.

- **Request:** {"email": "string (will be lowercased)", "password": "string (min 8 chars)"}
- **Response:** {"access_token": "string", "user": {"id": "string", "email": "string", "display_name": "string|null", "avatar_url": "string|null", "auth_provider": "string", "email_verified": "boolean"}}
- **Status codes:**
  - `200` — Registration succeeds. The user dict MUST include an `email_verified` field set to `false`. The returned bearer token is valid but must not grant access to sensitive operations until verification is complete.
  - `409` — An account already exists for this (lowercased) email. Response body: {"error": "account_exists"}.
  - `400` — The password does not meet strength requirements.

### `POST /api/auth/email/verify-request` **(new)**

Initiate the email verification flow. Generates a single-use, short-lived verification token and returns it in the response body (observable substitute for the email).

- **Request:** Authorization: Bearer <access_token> (from registration). No body required.
- **Response:** {"verification_token": "string"}
- **Status codes:**
  - `200` (non-production, i.e. the token-exposing environment) — body EXACTLY
    `{"verification_token": "<string>"}`. The token is also what would be sent
    via email; returning it here is the grading-observable substitute.
  - `200` (production, token hidden) — body EXACTLY `{"status": "sent"}`. The
    `verification_token` key MUST be absent — not present-and-null, not an
    empty object. This is the shape the acceptance oracle never exercises (it
    always runs non-production), so it is fixed here purely to stop the
    implementer and the reviewer disagreeing about an unstated body.
  - `401` — No valid access token is provided. Body: `{"error": "unauthorized"}`.
  - `409` — The account is already verified. Body: `{"error": "already_verified"}`.

### `POST /api/auth/email/verify` **(new)**

> **Error vocabulary for this endpoint, fixed 2026-08-09.** This route returns
> EXACTLY two error codes and no others. A token belonging to an
> already-verified account is `{"error": "invalid_token"}` — the same shape as
> any other unusable token, deliberately: a caller must not be able to probe
> which addresses are verified. Do NOT introduce an `already_verified` error
> here; that code exists only on `verify-request` (409).

Consume a verification token to mark the account as verified.

- **Request:** {"verification_token": "string"}
- **Response:** {"message": "email_verified"}
- **Status codes:**
  - `200` — Token is valid, not expired, and belongs to an unverified account. The account is now verified and the token is invalidated.
  - `400` — Token is expired. Response body: {"error": "token_expired"}.
  - `400` — Token is invalid or has already been used. Response body: {"error": "invalid_token"}.

### `GET /api/auth/me` _(existing)_

Return the current user profile. The `user` dict MUST include an `email_verified` boolean field. This is the endpoint used to inspect verification state and to test authorization gating.

- **Request:** Authorization: Bearer <access_token>
- **Response:** {"id": "string", "email": "string", "display_name": "string|null", "avatar_url": "string|null", "auth_provider": "string", "email_verified": "boolean"}
- **Status codes:**
  - `200` — Valid token is provided. The `email_verified` field reflects the current verification state: `false` immediately after registration, `true` after successful verification.
  - `401` — Token is missing, expired, or invalid.

### `DELETE /api/auth/email/verify-token` **(new)**

Expire the verification token early (invalidate before its natural TTL) so a single-use constraint can be demonstrated within a short test window. This is an observable substitute for waiting for expiry.

- **Request:** Authorization: Bearer <access_token>
- **Response:** {"message": "token_invalidated"}
- **Status codes:**
  - `200` — An outstanding token exists for the authenticated user and is invalidated.
  - `401` — No valid access token is provided.
  - `404` — No outstanding verification token exists for this user.

## Acceptance criteria — how each is observed

### 1. New email/password accounts require successful verification before sensitive operations

- **Status:** graded by the acceptance oracle (HTTP)
- **How:** 1. POST /api/auth/email/register with a unique email (using $ACCEPTANCE_RUN_ID) and a valid password; capture the access_token. 2. **Prove the GATE, not just the flag:** with that bearer token, POST /api/goals with a valid goal body. It MUST be refused with 403 — an unverified account cannot perform a sensitive operation. (`POST /api/goals` is a real route, is authenticated, and creates state, so a no-op implementation cannot satisfy this the way a status-code-only or field-inspection check could.) 3. POST /api/auth/email/verify-request with the Bearer token to obtain a verification_token. 4. POST /api/auth/email/verify with {"verification_token": "<token>"}. Expect 200 and `{"message": "email_verified"}`. 5. Re-issue the bearer token via POST /api/auth/email/login, then POST /api/goals again with an equivalent body. It MUST now succeed (2xx) and the response MUST carry the created goal's `id`. The before/after pair on the SAME sensitive route is the evidence: refused while unverified, allowed once verified. Assert `email_verified` is `true` on GET /api/auth/me as a secondary check only — never as the primary observable.
- **Endpoints:** `/api/auth/email/register`, `/api/goals`, `/api/auth/email/login`, `/api/auth/email/verify-request`, `/api/auth/email/verify`, `/api/auth/me`

### 2. Verification tokens are single-use, short-lived, and invalidated after use

- **Status:** graded by the acceptance oracle (HTTP)
- **How:** Single-use: 1. Register, obtain token via /api/auth/email/verify-request. 2. Use it successfully via /api/auth/email/verify (expect 200). 3. Attempt to use the same token again via /api/auth/email/verify. Expect 400 with {"error": "invalid_token"}. Short-lived: 4. Register a second account, obtain token. 5. Force-expire the token via DELETE /api/auth/email/verify-token (expect 200). 6. Immediately attempt /api/auth/email/verify with that token. Expect 400 with {"error": "token_expired"} (the expired-by-deletion and naturally-expired cases must be indistinguishable in their observable effect: the token is no longer usable).
- **Endpoints:** `/api/auth/email/register`, `/api/auth/email/verify-request`, `/api/auth/email/verify`, `/api/auth/email/verify-token`

### 3. Tests cover unverified vs verified authorization behavior

- **Status:** verified by the implementation's own test suite, not the oracle
- **How:** This criterion is about the implementation's own test suite. The grader cannot inspect internal tests, code coverage, or test runner output. The implementer must write tests that exercise unverified vs verified authorization gating. Coverage merge gates in the CI pipeline verify this requirement.

## Observability affordances and their constraints

POST /api/auth/email/verify-request returns the verification_token in the response body as an observable substitute for the out-of-band email. This is acceptable only if the token is also sent via email in production; the response-body leak must be guarded by an environment check (e.g., only in a non-production or acceptance environment) so it is never exposed in live traffic. DELETE /api/auth/email/verify-token exists solely to invalidate tokens on demand for grading; it must require a valid Bearer token and must not be usable to invalidate another user's token. Neither affordance may weaken the production flow.

---

## Operator ratification — 2026-08-09

Ratified with one correction, recorded here because the reasoning matters more
than the edit.

**AC1's observable was too weak as generated.** The contract author concluded
"no sensitive-operation endpoint exists in the route table" and designated
`GET /api/auth/me` as the gating point, checking that `email_verified` is
`false`. That inspects a FLAG; it does not prove a GATE. An implementation that
adds the field to the response and enforces nothing would satisfy it — green
meaning less than it appears.

`POST /api/goals` does exist in the route table, is authenticated, creates
state, and is exactly the route the earlier dev attempt gated. AC1 now asserts
the before/after pair on that route: **403 while unverified, 2xx once
verified**. The flag check is retained as a secondary signal only.

This is the failure mode the ratification step exists for: the author cannot
audit its own choice of observable, and the weakness is invisible in a green
run. See `apps/factory/context/modules/personas.md` (Failure modes).

## Ratification addendum — 2026-08-09 (second pass)

Story 177 reached `blocked_review_nonconvergent` after two review cycles with an
unmoved score (0.85 → 0.85). Diagnosis: **not** a dev or reviewer failure — two
response bodies were never specified, so every choice the implementer made was
a contract violation to the reviewer.

1. `verify-request` 200 in the token-HIDDEN environment. The implementer tried
   `{"verification_token": null}` (cycle 1 finding) then `{}` (cycle 2 finding);
   the contract defined only the token-exposing shape. Now fixed to
   `{"status": "sent"}`, key absent.
2. The already-verified case on `verify`. The implementer moved from
   `invalid_token` to `already_verified`; the reviewer then noted, correctly,
   that the spec does not define `already_verified` on that route. Now fixed to
   `invalid_token`, with the reason (no verification-status oracle for an
   unauthenticated caller).

Generalised into the `contract` persona as rule 2c and enforced by requiring a
`body` on every status code — see the paired factory PR.
