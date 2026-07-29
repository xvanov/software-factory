---
title: Build Docker production deployment and enable factory auto-deploy for sacrifice
type: infra
priority: p1
explore: true
created_at: '2026-07-18T17:05:00.000000+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Build Docker production deployment and enable factory auto-deploy for sacrifice

## Why
The factory ships code to `main`, but nothing reaches the running production backend. `apps/sacrifice/config.yaml` has `deploy.enabled: false` because the Docker deploy artifacts it references (`docker-compose.prod.yml`, Dockerfiles) do not exist yet. As a result, every merged change — CSRF protection, abuse controls, strict proof schemas, secret governance, mobile parity — accumulates on `main` while the live app on `localhost:8000` (served publicly via the `sacrifice.rentus.homes` cloudflared tunnel) keeps running old code. We need a real deploy path so merged `main` reaches production.

## What
Produce the deployment artifacts the config already references, then enable auto-deploy:
- A backend `Dockerfile` (FastAPI/uvicorn on port 8000) and any frontend build artifacts required to run the app.
- A `docker-compose.prod.yml` at the repo root that builds and runs the full stack (backend :8000, Postgres, Redis/Celery as the app requires).
- Confirm the health endpoint the config points at works post-boot (`curl -fsS http://localhost:8000/healthz` — reconcile with the existing `/api/health` if they differ).
- Verify `docker compose -f docker-compose.prod.yml build` then `up -d` succeed, the health check passes, and the running backend serves current `main`.
- Provide a working rollback (`docker-compose.prod.yml.previous` is referenced by `deploy.rollback_command`).
- Once the above is verified end-to-end, flip `deploy.enabled: true` in `apps/sacrifice/config.yaml` so future merges auto-deploy through the factory's existing deploy → health-check → smoke → rollback machinery.

## Acceptance criteria
- [ ] `docker compose -f docker-compose.prod.yml build && docker compose -f docker-compose.prod.yml up -d` brings up the full stack cleanly.
- [ ] The configured health check passes after deploy; a failed health check triggers rollback, not a broken live app.
- [ ] A merge to `main` results in the live backend (`localhost:8000`, reachable via `https://sacrifice.rentus.homes`) serving the merged code.
- [ ] Mobile `POST /api/auth/email/login` and `/register` are verified against the freshly deployed backend (regression guard: the newly-merged CSRF protection must NOT break the Expo Go mobile auth flow — those routes must still succeed for the mobile client).
- [ ] Deploy is idempotent and safe to re-run; the smoke gate (`make smoke`) gates the deploy.

## Notes for triage
This is production infrastructure on a live system. The first real auto-deploy changes what runs in production, so the smoke gate + health-check + rollback must be proven before `deploy.enabled` is flipped. Explore the existing backend/ layout, the `/api/health` route, and how the app is currently run on :8000 before designing the compose file.
