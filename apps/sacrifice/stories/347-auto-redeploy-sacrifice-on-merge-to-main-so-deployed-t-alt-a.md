# Story

## Story
As the host operator for Sacrifice,
I want an automatic redeploy mechanism on the deployed host that tracks `origin/main`,
so that the running instance matches main without manual deploy steps.

## Acceptance Criteria
- [ ] When origin/main advances, the host checkout fast-forwards to origin/main (no manual step) and the four sacrifice-* user services restart to pick up the new code.
- [ ] A post-restart health check (curl -fsS http://localhost:8000/healthz) must pass; on failure the deploy alerts and does not leave services broken.
- [ ] The mechanism only redeploys on a genuine main advance (idempotent; no restart when already at origin/main) and logs each action.
- [ ] Documented: how it is triggered (poll timer or webhook) and how to disable it.
- [ ] Verified once end-to-end: a commit merged to main appears running on the deployed instance (local == remote == deployed) without manual intervention.

### Testable Claims (EARS)
AC1.1: WHEN `origin/main` advances, THE host checkout SHALL fast-forward to `origin/main` with no manual step.
AC1.2: WHEN the host checkout fast-forwards to `origin/main`, THE deployment mechanism SHALL restart the four `sacrifice-*` user services to pick up the new code.
AC2.1: WHEN the four `sacrifice-*` user services restart after deploy, THE deployment mechanism SHALL run a post-restart health check using `curl -fsS http://localhost:8000/healthz`.
AC2.2: WHEN the post-restart health check fails, THE deployment mechanism SHALL alert.
AC2.3: WHEN the post-restart health check fails, THE deployment mechanism SHALL not leave services broken.
AC3.1: WHEN `origin/main` has not genuinely advanced, THE deployment mechanism SHALL not redeploy.
AC3.2: WHEN the host checkout is already at `origin/main`, THE deployment mechanism SHALL not restart services.
AC3.3: WHEN the deployment mechanism performs or skips a deploy action, THE deployment mechanism SHALL log each action.
AC4.1: WHEN operators read the deployment documentation, THE documentation SHALL explain how the mechanism is triggered.
AC4.2: WHEN operators read the deployment documentation, THE documentation SHALL explain how to disable the mechanism.
AC5.1: WHEN a commit is merged to main and the mechanism runs end-to-end once, THE deployed instance SHALL be verified to be running that merged commit without manual intervention.
AC5.2: WHEN the end-to-end verification is completed, THE verification record SHALL demonstrate `local == remote == deployed`.

## Tasks / Subtasks
- [ ] Confirm implementation narrow-read scope
  - [ ] Cover host-side auto-redeploy mechanism only
  - [ ] Use poll timer or webhook only if it satisfies stated ACs
  - [ ] Keep scope to deployed host at `/home/k/sacrifice`
- [ ] Add deploy execution artifact(s)
  - [ ] Add host-executable script or command wrapper for redeploy checks
  - [ ] Fetch `origin/main` before deploy decision
  - [ ] Detect whether local checkout is behind `origin/main`
  - [ ] Exit cleanly without restart when already current
  - [ ] Fast-forward checkout to `origin/main` on genuine advance only
- [ ] Restart required user services
  - [ ] Restart `sacrifice-backend`
  - [ ] Restart `sacrifice-frontend`
  - [ ] Restart `sacrifice-celery`
  - [ ] Restart `sacrifice-expo-go`
- [ ] Add post-restart health gate
  - [ ] Run `curl -fsS http://localhost:8000/healthz`
  - [ ] Treat health-check failure as deploy failure
  - [ ] Emit failure signal via chosen alert path
  - [ ] Ensure failure handling does not leave services broken
- [ ] Add idempotency and logging
  - [ ] Log no-op when already at `origin/main`
  - [ ] Log fetch / decision / restart / health-check / failure actions
  - [ ] Avoid duplicate restart on unchanged revision
- [ ] Wire automatic trigger
  - [ ] Add host trigger mode implementation: poll timer or webhook
  - [ ] Ensure trigger invokes the same idempotent redeploy path
  - [ ] Ensure repeated trigger executions remain safe
- [ ] Document operations behavior
  - [ ] Document trigger mode used
  - [ ] Document disable procedure
  - [ ] Document where logs and failure signals are observed
- [ ] Verify end-to-end once
  - [ ] Exercise merged-commit path from `main` to deployed host
  - [ ] Record evidence that deployed revision matches merged commit
  - [ ] Record that no manual intervention was required

## Dev Notes
- Narrow-read story scope: produce the full host-level auto-redeploy capability described in the direction as one infra slice, including detection, fast-forward, service restart, health gate, automatic trigger, logging, failure signaling, documentation, and one end-to-end verification record.
- `flow.md` is absent in the direction.
- `api_spec.md` is absent in the direction.
- Direction acceptance criteria are explicit; do not weaken them during implementation or review.
- Alerting mechanism is not concretely specified by the direction. Implementation must choose the simplest observable host-path available and document the exact behavior used; review against the verbatim AC, not an invented threshold.
- “Does not leave services broken” is required but not implementation-prescriptive. Dev must make failure handling explicit and testable in the chosen host mechanism.

### Context pointers to load
- [Source: context/project.md#Identity]
- [Source: context/project.md#Stack]
- [Source: context/project.md#Top-level layout]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on replay defenses or session invalidation]
- [Source: context/navigation.md#When working on migration or machine bootstrap]

### Verbatim direction acceptance criteria
- [ ] When origin/main advances, the host checkout fast-forwards to origin/main (no manual step) and the four sacrifice-* user services restart to pick up the new code.
- [ ] A post-restart health check (curl -fsS http://localhost:8000/healthz) must pass; on failure the deploy alerts and does not leave services broken.
- [ ] The mechanism only redeploys on a genuine main advance (idempotent; no restart when already at origin/main) and logs each action.
- [ ] Documented: how it is triggered (poll timer or webhook) and how to disable it.
- [ ] Verified once end-to-end: a commit merged to main appears running on the deployed instance (local == remote == deployed) without manual intervention.

## References
- `backend/app/main.py`
- `backend/app/config.py`
- `backend/cli/main.py`
- `docker-compose.yml`
- `scripts/migration/`
- `context/project.md`
- `context/navigation.md`

## Dev Agent Record
- Status: Not started
- Agent: TBD
- Branch: TBD
- Notes:
  - TBD

## Senior Developer Review
- Status: Pending
- Reviewer: TBD
- Review notes:
  - TBD

## Review Follow-ups
- None yet.
