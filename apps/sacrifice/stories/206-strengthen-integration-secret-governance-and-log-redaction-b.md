# Story
**Title:** Strengthen integration secret governance and log redaction — broad read
**Slug:** strengthen-integration-secret-governance-and-log-redaction-b
**Scope:** backend

## Acceptance Criteria
- [ ] Secrets are loaded from approved secure sources only, not defaults/hardcoded fallbacks
- [ ] Application logs redact tokens/keys and tests assert redaction behavior
- [ ] Documented rotation and scope policy exists for Stripe/OAuth/provider credentials

### Testable Claims (EARS)
AC1.1: WHEN application configuration loads integration credentials, THE backend settings layer SHALL accept secrets from approved secure sources only
AC1.2: WHEN application configuration loads integration credentials, THE backend settings layer SHALL NOT use defaults or hardcoded fallbacks as secret values
AC2.1: WHEN application code emits logs containing tokens or keys, THE logging path SHALL redact the sensitive values in observable log output
AC2.2: WHEN redaction behavior is implemented, THE test suite SHALL assert the redaction behavior
AC3.1: WHEN operators need guidance for Stripe, OAuth, and provider credentials, THE project documentation SHALL include a documented rotation and scope policy

## Tasks / Subtasks
- [ ] Audit `backend/app/config.py` for integration secret fields and all default/fallback secret-loading paths
- [ ] Define approved secret-source guardrails in backend settings for integration credentials only
- [ ] Remove or block insecure defaults/hardcoded secret fallbacks in backend settings
- [ ] Preserve non-secret config behavior unless directly required by secret-source enforcement
- [ ] Identify logging entry points that can emit tokens, keys, headers, bearer values, API keys, or DSNs
- [ ] Implement centralized log redaction for tokens/keys at the logging boundary
- [ ] Ensure redaction applies to structured and stringified log payloads used by current backend paths
- [ ] Add backend tests covering approved secret loading vs rejected fallback behavior
- [ ] Add backend tests asserting token/key redaction in observable logs
- [ ] Add or update canonical documentation for credential rotation and minimum-scope policy
- [ ] Reference the canonical doc location from code comments or nearby docs only if an existing pattern supports it
- [ ] Validate no acceptance criterion remains uncovered by code, tests, or docs changes

## Dev Notes
### Scope and sequencing
- Broad-read story consolidates the direction's three acceptance criteria into one backend-led implementation slice.
- PM decomposition context exists, but this story is the single source of truth for this assigned record.
- `flow.md` not provided by direction.
- Backend scope is a primary consumer of `api_spec.md`, but none was provided by direction.

### flow.md
(none)

### api_spec.md
(none)

### Verbatim direction acceptance criteria
- [ ] Secrets are loaded from approved secure sources only, not defaults/hardcoded fallbacks
- [ ] Application logs redact tokens/keys and tests assert redaction behavior
- [ ] Documented rotation and scope policy exists for Stripe/OAuth/provider credentials

### Context pointers to load
- [Source: context/project.md#Identity]
- [Source: context/project.md#Stack]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/navigation.md#When working on replay defenses or session invalidation]
- [Source: context/current-state.md#Auth hardening focus]
- [Source: context/current-state.md#Configuration and secrets]
- [Source: context/current-state.md#Logging and observability]
- [Source: context/modules/auth.md#Configuration]
- [Source: context/modules/auth.md#Token lifecycle]
- [Source: context/modules/security.md#Secrets handling]
- [Source: context/modules/security.md#Logging and redaction]
- [Source: context/modules/backend.md#Configuration]
- [Source: context/modules/backend.md#Testing]

### Implementation constraints
- Work from existing backend settings and auth/security primitives called out in context: FastAPI backend, JWT bearer tokens, Fernet-encrypted sensitive stored tokens, and configured integrations including Stripe, Redis, PostgreSQL, Google, GitHub, YouTube, and Azure Foundry.
- OAuth browser/mobile flows already avoid returning raw access tokens to the frontend; maintain that posture while hardening backend secret governance.
- Treat bearer-token compromise as high impact because shared auth dependencies reach goals, payments, notifications, uploads, dashboard data, and chat-adjacent flows.
- Do not introduce manual server-start workflow changes; follow repo guidance in `PROMPT.md`.
- This story may touch canonical docs only where needed to satisfy the rotation/scope policy criterion; do not write forbidden ADR/archive/history paths.

### Expected touch areas
- `backend/app/config.py`
- backend logging setup/utilities in the current logging path
- backend tests covering config behavior and logging output
- canonical documentation path within allowed docs set for rotation/scope policy

### Gaps / review flags
- If `context/current-state.md` or module docs do not contain the referenced sections exactly, load the nearest existing section covering the same topic and record the mismatch in implementation notes.
- “Approved secure sources” is direction language; implementation must make the approved source list explicit in code/tests/docs without weakening the criterion.
- “Documented rotation and scope policy” requires a canonical doc location discoverable by operators and reviewers.

## References
- `prd.md`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/core/dependencies.py`
- `backend/app/routes/auth.py`
- `backend/app/services/auth.py`
- `backend/app/core/crypto.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_email_auth.py`
- `context/project.md`
- `context/navigation.md`
- `context/current-state.md`
- `context/modules/auth.md`
- `context/modules/security.md`
- `context/modules/backend.md`
- `context/sprint-status.yaml`

## Dev Agent Record
- Status: Not started
- Assigned record: `strengthen-integration-secret-governance-and-log-redaction-b`
- Notes: Awaiting implementation

## Senior Developer Review
- Pending

## Review Follow-ups
- None yet
