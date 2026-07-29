---
title: Auto-redeploy sacrifice on merge to main so deployed tracks main
type: infra
priority: p1
explore: true
created_at: '2026-07-23T17:34:06.668048+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Auto-redeploy sacrifice on merge to main so deployed tracks main

## Why

Merges to main do not reach the running instance; deploy is manual and drifts, so local != remote != deployed. Add a mechanism on this host that, when origin/main advances, fast-forwards the /home/k/sacrifice checkout to origin/main and restarts the systemd --user services (sacrifice-backend, sacrifice-frontend, sacrifice-celery, sacrifice-expo-go) with a health gate, so deployed == main.

## Acceptance Criteria

- [ ] When origin/main advances, the host checkout fast-forwards to origin/main (no manual step) and the four sacrifice-* user services restart to pick up the new code.
- [ ] A post-restart health check (curl -fsS http://localhost:8000/healthz) must pass; on failure the deploy alerts and does not leave services broken.
- [ ] The mechanism only redeploys on a genuine main advance (idempotent; no restart when already at origin/main) and logs each action.
- [ ] Documented: how it is triggered (poll timer or webhook) and how to disable it.
- [ ] Verified once end-to-end: a commit merged to main appears running on the deployed instance (local == remote == deployed) without manual intervention.
