---
title: Verify and enable the sacrifice production deploy (complete D088)
type: infra
priority: p1
explore: true
created_at: '2026-07-19T13:56:03.254678+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Verify and enable the sacrifice production deploy (complete D088)

## Why

D088 shipped the deploy artifacts (backend Dockerfile, docker-compose.prod.yml, rollback file) and they're on main, but deploy.enabled is still FALSE because the end-to-end deploy was never verified — and enabling it prematurely previously triggered a failing deploy that flipped the factory into fix-only mode. WHAT TO DO, in order, and CONSERVATIVELY: (1) Verify the prod stack builds and boots: `docker compose -f docker-compose.prod.yml build` then `up -d`; confirm the configured health check (`curl -fsS http://localhost:8000/healthz`) passes. (2) Run the real smoke journey against the freshly-deployed backend (register->login->create-goal->proof) to prove it actually serves. (3) Verify the mobile auth routes (POST /api/auth/email/login and /register) still succeed against the deployed backend (CSRF/abuse-control regression guard). (4) ONLY IF all of the above pass end-to-end, flip deploy.enabled=true in the FACTORY's apps/sacrifice/config.yaml so future merges auto-deploy. If ANY step fails, DO NOT enable — leave deploy.enabled=false, and clearly report exactly what failed in the Dev Agent Record so the operator can decide. Enabling a broken deploy is far worse than leaving it disabled. SCOPE: deploy artifacts + config + verification only; keep the diff minimal, do not refactor app code.

## Acceptance Criteria

- [ ] docker compose -f docker-compose.prod.yml build && up -d brings up the stack cleanly and /healthz passes.
- [ ] The smoke journey passes against the DEPLOYED backend (not just local).
- [ ] Mobile /api/auth/email/login and /register succeed against the deployed backend.
- [ ] deploy.enabled is flipped to true ONLY IF all verification passed; otherwise left false with a clear failure report.
- [ ] Diff is minimal (deploy artifacts/config/verification); no unrelated app refactoring.
