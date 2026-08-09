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
  - `200` — Token generated and returned. The token is also what would be sent via email; returning it here is the grading-observable substitute.
  - `401` — No valid access token is provided.
  - `409` — The account is already verified. Response body: {"error": "already_verified"}.

### `POST /api/auth/email/verify` **(new)**

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
- **How:** 1. POST /api/auth/email/register with a unique email (using $ACCEPTANCE_RUN_ID) and a valid password. Capture the access_token and assert the user.email_verified field in the 200 response is `false`. 2. Attempt a sensitive operation. Since no sensitive-operation endpoint exists in the route table, the contract designates GET /api/auth/me as the observable gating point: it must return 200 and the user dict regardless of verification state, but the `email_verified` field must be `false`, proving the account is unverified. 3. POST /api/auth/email/verify-request with the Bearer token to obtain a verification_token. 4. POST /api/auth/email/verify with {"verification_token": "<token>"}. Expect 200 and `{"message": "email_verified"}`. 5. GET /api/auth/me again with the same Bearer token. Assert `email_verified` is now `true`. This sequence proves the account transitions from unverified to verified and that the verification state is observable.
- **Endpoints:** `/api/auth/email/register`, `/api/auth/me`, `/api/auth/email/verify-request`, `/api/auth/email/verify`

### 2. Verification tokens are single-use, short-lived, and invalidated after use

- **Status:** graded by the acceptance oracle (HTTP)
- **How:** Single-use: 1. Register, obtain token via /api/auth/email/verify-request. 2. Use it successfully via /api/auth/email/verify (expect 200). 3. Attempt to use the same token again via /api/auth/email/verify. Expect 400 with {"error": "invalid_token"}. Short-lived: 4. Register a second account, obtain token. 5. Force-expire the token via DELETE /api/auth/email/verify-token (expect 200). 6. Immediately attempt /api/auth/email/verify with that token. Expect 400 with {"error": "token_expired"} (the expired-by-deletion and naturally-expired cases must be indistinguishable in their observable effect: the token is no longer usable).
- **Endpoints:** `/api/auth/email/register`, `/api/auth/email/verify-request`, `/api/auth/email/verify`, `/api/auth/email/verify-token`

### 3. Tests cover unverified vs verified authorization behavior

- **Status:** verified by the implementation's own test suite, not the oracle
- **How:** This criterion is about the implementation's own test suite. The grader cannot inspect internal tests, code coverage, or test runner output. The implementer must write tests that exercise unverified vs verified authorization gating. Coverage merge gates in the CI pipeline verify this requirement.

## Observability affordances and their constraints

POST /api/auth/email/verify-request returns the verification_token in the response body as an observable substitute for the out-of-band email. This is acceptable only if the token is also sent via email in production; the response-body leak must be guarded by an environment check (e.g., only in a non-production or acceptance environment) so it is never exposed in live traffic. DELETE /api/auth/email/verify-token exists solely to invalidate tokens on demand for grading; it must require a valid Bearer token and must not be usable to invalidate another user's token. Neither affordance may weaken the production flow.
