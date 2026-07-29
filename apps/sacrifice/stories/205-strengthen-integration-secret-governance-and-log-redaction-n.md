# Story
**Title:** Strengthen integration secret governance and log redaction — narrow read
**Slug:** strengthen-integration-secret-governance-and-log-redaction-n
**Scope:** backend

## Acceptance Criteria
- [ ] Secrets are loaded from approved secure sources only, not defaults/hardcoded fallbacks
- [ ] Application logs redact tokens/keys and tests assert redaction behavior
- [ ] Documented rotation and scope policy exists for Stripe/OAuth/provider credentials

### Testable Claims (EARS)
AC1.1: WHEN backend settings load integration secrets, THE configuration layer SHALL accept approved secure sources only
AC1.2: WHEN backend settings load integration secrets, THE configuration layer SHALL NOT use defaults or hardcoded fallbacks for secrets
AC2.1: WHEN application logs include tokens or keys, THE logging path SHALL redact those tokens or keys
AC2.2: WHEN redaction behavior is implemented, THE test suite SHALL assert the redaction behavior
AC3.1: WHEN operators need guidance for Stripe, OAuth, or provider credentials, THE system documentation SHALL include a rotation and scope policy for those credentials

## Tasks / Subtasks
- [ ] Audit `backend/app/config.py` secret-bearing settings for defaults, literals, and fallback chains
- [ ] Define approved secret-source rules for backend configuration loading
- [ ] Remove or block insecure default/hardcoded secret fallbacks in backend settings
- [ ] Fail fast with explicit validation on missing required secrets from approved sources
- [ ] Identify backend logging entry points that can emit tokens, keys, headers, DSNs, or provider credentials
- [ ] Add centralized redaction at the logging boundary for sensitive token/key material
- [ ] Ensure redaction preserves log usefulness without exposing secret values
- [ ] Add or update backend tests covering approved secret-source enforcement
- [ ] Add or update backend tests covering log redaction behavior
- [ ] Document credential rotation and minimum-scope policy in canonical docs path selected during implementation
- [ ] Cross-check implementation against all AC EARS claims before handoff

## Dev Notes
### Scope boundary
- Narrow read for this invocation: prepare one backend-centered story that covers the direction at integration points owned by backend config and backend logging boundaries.
- PM decomposition context indicates likely downstream separation into backend/test/docs slices; this story remains source-of-truth for the assigned record and should sequence work so code changes land before any docs-only refinements if the chain later splits execution.

### flow.md
(none)

### api_spec.md
(none)

### Direction acceptance criteria (verbatim)
- [ ] Secrets are loaded from approved secure sources only, not defaults/hardcoded fallbacks
- [ ] Application logs redact tokens/keys and tests assert redaction behavior
- [ ] Documented rotation and scope policy exists for Stripe/OAuth/provider credentials

### Required context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Stack]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/navigation.md#When working on replay defenses or session invalidation]
- [Source: context/current-state.md#auth-and-session-hardening-overview]
- [Source: context/current-state.md#security-posture-and-open-gaps]
- [Source: context/modules/auth.md#configuration-and-token-lifecycle]
- [Source: context/modules/security.md#secret-handling-and-sensitive-data]
- [Source: context/modules/backend.md#configuration]
- [Source: context/modules/backend.md#logging-and-observability]
- [Source: context/modules/frontend.md#stored-auth-state]

### Implementation notes
- Backend settings are explicitly called out in PM notes as `backend/app/config.py`; treat that file as the primary enforcement point for approved secret-source loading.
- Existing integrations in scope from project context: Stripe, Google OAuth, GitHub OAuth, YouTube, Redis, PostgreSQL, Azure Foundry.
- Secret governance work is limited to removing/blocking insecure secret-loading paths; do not broaden into unrelated auth features.
- Logging hardening must focus on observable application logs and redaction of tokens/keys without changing functional API behavior.
- Tests are mandatory because the direction explicitly states redaction behavior must be asserted.
- Documentation requirement is part of this story's acceptance scope; implementation should place operator-facing policy in a canonical allowed doc path only.
- Do not write to forbidden decision/archive/history paths.
- If `context/current-state.md` section names differ slightly at execution time, use the matching auth/security sections present in the prelude before coding.
- Because bearer-token compromise is high impact across goals, payments, notifications, uploads, dashboard data, and chat-adjacent flows, prioritize coverage for any logger path that can capture auth headers or provider credentials.
- Preserve the current one-time `auth_code` exchange flow; this story is about secret governance and log redaction, not OAuth flow redesign.

## References
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/core/dependencies.py`
- `backend/app/routes/auth.py`
- `backend/app/services/auth.py`
- `backend/app/core/crypto.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_email_auth.py`
- `frontend/services/auth.ts`
- `backend/cli/client.py`
- `context/project.md`
- `context/navigation.md`
- `context/current-state.md`
- `context/modules/auth.md`
- `context/modules/security.md`
- `context/modules/backend.md`

## Dev Agent Record
- Status: Not started
- Agent: TBD
- Branch: TBD
- Notes: TBD

## Senior Developer Review
- Status: Pending
- Reviewer: TBD
- Notes: Verify no secret fallback survives in settings, verify redaction is centralized and regression-tested, verify docs path is canonical.

## Review Follow-ups
- None yet.
