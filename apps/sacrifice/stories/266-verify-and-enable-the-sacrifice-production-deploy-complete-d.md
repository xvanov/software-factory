# Story

## Story
As an operator of the Sacrifice factory deploy pipeline,
I want the production deploy path proven end-to-end before auto-deploy is enabled,
so that `deploy.enabled=true` is only set after the prod compose stack builds, boots, answers health checks, and serves the required regression journeys.

## Acceptance Criteria
- [ ] docker compose -f docker-compose.prod.yml build && up -d brings up the stack cleanly and /healthz passes.
- [ ] The smoke journey passes against the DEPLOYED backend (not just local).
- [ ] Mobile /api/auth/email/login and /register succeed against the deployed backend.
- [ ] deploy.enabled is flipped to true ONLY IF all verification passed; otherwise left false with a clear failure report.
- [ ] Diff is minimal (deploy artifacts/config/verification); no unrelated app refactoring.

### Testable Claims (EARS)
AC1.1: WHEN `docker compose -f docker-compose.prod.yml build && up -d` is executed for the production stack, THE deployment artifact set SHALL bring up the stack cleanly
AC1.2: WHEN the deployed stack is running, THE deployed backend SHALL respond successfully to `/healthz`
AC2.1: WHEN the real smoke journey is run against the deployed backend, THE deployed backend SHALL pass the smoke journey
AC2.2: WHEN the smoke journey is run for verification, GIVEN the target backend is the deployed stack, THE verification flow SHALL use the DEPLOYED backend and not just local services
AC3.1: WHEN `POST /api/auth/email/login` is sent to the deployed backend, THE deployed backend SHALL succeed
AC3.2: WHEN `POST /api/auth/email/register` is sent to the deployed backend, THE deployed backend SHALL succeed
AC4.1: WHEN all verification passed end-to-end, THE factory config SHALL flip `deploy.enabled` to `true`
AC4.2: WHEN any verification step fails, THE factory config SHALL remain with `deploy.enabled=false`
AC4.3: WHEN any verification step fails, THE Dev Agent Record SHALL contain a clear failure report
AC5.1: WHEN implementing this story, THE resulting diff SHALL remain minimal and limited to deploy artifacts, config, and verification
AC5.2: WHEN implementing this story, THE changes SHALL exclude unrelated app refactoring

## Tasks / Subtasks
- [x] Inspect current deploy assets and gating config
  - [x] Confirm `docker-compose.prod.yml` exists and is the target artifact
  - [x] Confirm current `deploy.enabled` value in `apps/sacrifice/config.yaml`
  - [x] Identify existing prod health endpoint path and required env/config inputs
- [x] Codify prod compose build/boot/health verification
  - [x] Add or update repeatable verification command/script for `docker compose -f docker-compose.prod.yml build`
  - [x] Add or update repeatable verification command/script for `docker compose -f docker-compose.prod.yml up -d`
  - [x] Add or update verification step for `curl -fsS http://localhost:8000/healthz`
  - [x] Keep any deploy-artifact fix minimal and limited to satisfying boot/health verification
- [x] Codify deployed smoke journey verification
  - [x] Run against deployed backend endpoint, not app-local test harness only
  - [x] Cover register -> login -> create-goal -> proof
  - [x] Capture pass/fail output usable by operator review
- [x] Codify deployed mobile email auth regression verification
  - [x] Verify `POST /api/auth/email/register` against deployed backend
  - [x] Verify `POST /api/auth/email/login` against deployed backend
  - [x] Capture pass/fail output usable by operator review
- [x] Gate deploy enablement on verification result
  - [x] Flip `deploy.enabled=true` only after all verification steps pass end-to-end
  - [x] Leave `deploy.enabled=false` if any verification step fails
  - [x] Record exact failing step(s) in Dev Agent Record when blocked
- [x] Final minimal-diff audit
  - [x] Remove unrelated edits
  - [x] Confirm no app refactor was introduced beyond minimal deploy/config fix

## Dev Notes
- Scope boundary: infra-only narrow read. Sequence is authoritative: verify build/boot/health first, then deployed smoke journey, then deployed mobile auth regression, then conditionally flip `deploy.enabled`.
- Flow handling: no standalone `flow.md` file was provided with content.
- API spec handling: no standalone `api_spec.md` file was provided with content.
- If no verification path can be established without broader application refactoring, stop short of enablement, preserve `deploy.enabled=false`, and document exact blockers in Dev Agent Record.

### Direction acceptance criteria (verbatim)
- [ ] docker compose -f docker-compose.prod.yml build && up -d brings up the stack cleanly and /healthz passes.
- [ ] The smoke journey passes against the DEPLOYED backend (not just local).
- [ ] Mobile /api/auth/email/login and /register succeed against the deployed backend.
- [ ] deploy.enabled is flipped to true ONLY IF all verification passed; otherwise left false with a clear failure report.
- [ ] Diff is minimal (deploy artifacts/config/verification); no unrelated app refactoring.

### Direction context (verbatim excerpt)
# Verify and enable the sacrifice production deploy (complete D088)

## Why

D088 shipped the deploy artifacts (backend Dockerfile, docker-compose.prod.yml, rollback file) and they're on main, but deploy.enabled is still FALSE because the end-to-end deploy was never verified — and enabling it prematurely previously triggered a failing deploy that flipped the factory into fix-only mode. WHAT TO DO, in order, and CONSERVATIVELY: (1) Verify the prod stack builds and boots: `docker compose -f docker-compose.prod.yml build` then `up -d`; confirm the configured health check (`curl -fsS http://localhost:8000/healthz`) passes. (2) Run the real smoke journey against the freshly-deployed backend (register->login->create-goal->proof) to prove it actually serves. (3) Verify the mobile auth routes (POST /api/auth/email/login and /register) still succeed against the deployed backend (CSRF/abuse-control regression guard). (4) ONLY IF all of the above pass end-to-end, flip deploy.enabled=true in the FACTORY's apps/sacrifice/config.yaml so future merges auto-deploy. If ANY step fails, DO NOT enable — leave deploy.enabled=false, and clearly report exactly what failed in the Dev Agent Record so the operator can decide. Enabling a broken deploy is far worse than leaving it disabled. SCOPE: deploy artifacts + config + verification only; keep the diff minimal, do not refactor app code.

### Context pointers to load
- [Source: context/project.md#Identity]
- [Source: context/project.md#Stack]
- [Source: context/project.md#Top-level layout]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/navigation.md#When working on replay defenses or session invalidation]
- [Source: context/navigation.md#When working on migration or machine bootstrap]

## References
- `docker-compose.prod.yml`
- `apps/sacrifice/config.yaml`
- `backend/app/main.py`
- `backend/app/routes/auth.py`
- `backend/app/routes/goals.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_email_auth.py`
- `frontend/services/auth.ts`
- `PROMPT.md`

## Dev Agent Record
- Status: BLOCKED (prod compose boot failed on host port conflict; deploy gate preserved as false)
- Verification target: deployed stack from `docker-compose.prod.yml`
- Completion Notes:
  - Implemented deploy verification orchestration in `scripts/verify-deploy.sh` with ordered build -> up -> health -> deployed smoke -> deployed mobile email auth checks and explicit BLOCKED reporting when compose boot/health is not available. Script is executable and bash-syntax-clean.
  - Implemented gate + mobile-auth helpers in `scripts/verify_deploy_lib.py` (stdlib-only for host portability) so `deploy.enabled` is set to `true` only on all-pass verification via the `--enable` CLI, and forced/stays `false` on any failed/blocked step via `--force-disable`. Includes `VerificationReport` collector, `apply_gate()` orchestrator, and deployed-target HTTP helpers (`verify_deployed_health`, `verify_deployed_mobile_register`, `verify_deployed_mobile_login`, `run_smoke_journey_against_deployed`).
  - Added regression coverage in `backend/tests/test_verify_deploy_lib.py` (27 tests) and `backend/tests/test_verify_deploy_script.py` (14 tests) for: config gate toggling (read/write/set/enable/disable/missing-key), `VerificationReport` pass/fail/mixed, `apply_gate` all-pass/fail/force-false/empty-report, deployed mobile auth and smoke helpers returning dict/string outputs on unreachable backends, CLI `gate-apply --enable`/`--force-disable`/`--reason`, script existence/executability/syntax, and end-to-end gate pipeline simulated across all six verification steps.
  - Story-scoped verifier tests: `41 passed` (`cd backend && uv run --extra dev pytest -q tests/test_verify_deploy_lib.py tests/test_verify_deploy_script.py`).
  - Full backend suite after final changes: `734 passed, 1 skipped` (`cd backend && uv run --extra dev pytest -q tests/`).
- Verification Evidence (latest run of `./scripts/verify-deploy.sh`):
  - `docker compose -f docker-compose.prod.yml build`: **PASS**.
  - `docker compose -f docker-compose.prod.yml up -d`: **FAIL** — `failed to bind host port 0.0.0.0:8000/tcp: address already in use`.
  - `curl -fsS http://localhost:8000/healthz`: **BLOCKED/FAILED** (compose boot failed).
  - Deployed smoke journey (`register -> login -> create-goal -> proof`): **BLOCKED/FAILED** (deployed backend was not healthy).
  - Deployed mobile `POST /api/auth/email/register`: **BLOCKED/FAILED** (deployed backend was not healthy).
  - Deployed mobile `POST /api/auth/email/login`: **BLOCKED/FAILED** (deployed backend was not healthy).
  - Final state of `/home/k/software-factory/apps/sacrifice/config.yaml`: `deploy.enabled: false`.
- Failure Report:
  - Failing command/step: `docker compose -f docker-compose.prod.yml up -d`.
  - Observed failure: host port bind conflict on `:8000` (`address already in use`).
  - Gate outcome: `deploy.enabled` remained `false` (no auto-enable performed). The verification script correctly exited 1 and reported the failing step.
  - To unblock: free port 8000 on the deploy host (or remap `docker-compose.prod.yml` to a different host port), then re-run `./scripts/verify-deploy.sh`.
- File List:
  - `scripts/verify-deploy.sh`
  - `scripts/verify_deploy_lib.py`
  - `backend/tests/test_verify_deploy_lib.py`
  - `backend/tests/test_verify_deploy_script.py`

## Senior Developer Review
- Verify the story preserved the deployment gate: no enablement without proof.
- Verify all verification steps target the deployed backend, not local-only mocks.
- Verify any file edits stay within deploy artifacts, verification wiring, and config.
- Verify Dev Agent Record contains explicit operator-readable failure detail when blocked.

## Review Follow-ups
- [x] Confirm verification evidence is attached for build, boot, health, smoke, and mobile auth
- [x] Confirm `deploy.enabled` changed only if all evidence passed
- [x] Confirm no unrelated app refactoring landed
