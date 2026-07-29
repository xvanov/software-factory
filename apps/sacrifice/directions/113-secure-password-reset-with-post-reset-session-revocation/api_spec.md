# API spec

POST /api/auth/password/reset/request  body {email}  -> 202 Accepted (always, to avoid user enumeration); if the email maps to a user, mint a single-use, short-TTL (<=30m), purpose="password_reset" signed token bound to the user id + a jti for single-use. Token delivery (email) is out of scope; do not leak the token in the response.
POST /api/auth/password/reset/confirm  body {token, new_password}  -> 200 on success: validate signature/purpose/expiry/single-use(jti not already consumed), enforce the same password policy as register, set the new password hash, and ROTATE user.auth_session_id so every previously-issued JWT/session is revoked. 400 on an invalid/expired/reused token.
