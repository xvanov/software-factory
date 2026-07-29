# Story

## Story
As the host operator for Sacrifice,
I want the deployed host to automatically detect `origin/main` advancement, fast-forward `/home/k/sacrifice`, restart the required `systemd --user` services, gate success on health, log outcomes, and document/verify the mechanism,
so that deployed == main without manual deploy drift.

## Acceptance Criteria
- [ ] When `origin/main` advances, the host checkout fast-forwards to `origin/main` (no manual step) and the four `sacrifice-*` user services restart to pick up the new code.
- [ ] A post-restart health check (`curl -fsS http://localhost:8000/healthz`) must pass; on failure the deploy alerts and does not leave services broken.
- [ ] The mechanism only redeploys on a genuine main advance (idempotent; no restart when already at `origin/main`) and logs each action.
- [ ] Documented: how it is triggered (poll timer or webhook) and how to disable it.
- [ ] Verified once end-to-end: a commit merged to main appears running on the deployed instance (local == remote == deployed) without manual intervention.

### Testable Claims (EARS)
AC1.1: WHEN `origin/main` advances, THE host checkout SHALL fast-forward to `origin/main` without a manual step.
AC1.2: WHEN the host checkout fast-forwards to `origin/main`, THE deployment mechanism SHALL restart the four `sacrifice-*` user services so they pick up the new code.
AC2.1: WHEN the four `sacrifice-*` user services have restarted, THE deployment mechanism SHALL run a post-restart health check using `curl -fsS http://localhost:8000/healthz`.
AC2.2: WHEN the post-restart health check fails, THE deployment mechanism SHALL alert.
AC2.3: WHEN the post-restart health check fails, THE deployment mechanism SHALL not leave services broken.
AC3.1: WHEN `origin/main` has not genuinely advanced, THE deployment mechanism SHALL not redeploy.
AC3.2: WHEN the host checkout is already at `origin/main`, THE deployment mechanism SHALL not restart services.
AC3.3: WHEN the deployment mechanism performs a deploy-related decision or action, THE deployment mechanism SHALL log each action.
AC4.1: WHEN an operator reads the deployment documentation, THE documentation SHALL explain how the mechanism is triggered.
AC4.2: WHEN an operator reads the deployment documentation, THE documentation SHALL explain how to disable the mechanism.
AC5.1: WHEN a commit is merged to `main`, THE deployed instance SHALL be verified once to be running that merged commit without manual intervention.
AC5.2: WHEN the end-to-end verification is performed, THE verification SHALL show local == remote == deployed.

## Tasks / Subtasks
- [ ] Implement host-side deploy mechanism covering detection, fast-forward, restart, health gate, logging, and failure signaling.
  - [ ] Fetch and compare local checkout vs `origin/main` in `/home/k/sacrifice`.
  - [ ] Exit cleanly with logged no-op when already at `origin/main`.
  - [ ] Fast-forward checkout to `origin/main` only on genuine advance.
  - [ ] Restart `sacrifice-backend`.
  - [ ] Restart `sacrifice-frontend`.
  - [ ] Restart `sacrifice-celery`.
  - [ ] Restart `sacrifice-expo-go`.
  - [ ] Run `curl -fsS http://localhost:8000/healthz` after restart.
  - [ ] Emit failure alert via chosen host-observable path.
  - [ ] Ensure failure handling does not leave services broken.
  - [ ] Log each decision and action.
- [ ] Wire automatic trigger on the host.
  - [ ] Choose trigger mode permitted by direction: poll timer or webhook.
  - [ ] Create host automation wiring for automatic execution.
  - [ ] Ensure trigger path preserves idempotent no-op behavior.
- [ ] Add operator documentation.
  - [ ] Document trigger mode in canonical repo docs.
  - [ ] Document log location / observation path.
  - [ ] Document disable procedure.
- [ ] Record one end-to-end verification.
  - [ ] Exercise mechanism with a merged commit to `main`.
  - [ ] Capture evidence that deployed instance runs the merged commit.
  - [ ] Capture evidence that no manual deploy intervention was required.

## Dev Notes
- Scope note: broad-read story intentionally spans the full direction outcome in one infra story: detection, deploy execution, host trigger wiring, docs, and one end-to-end verification artifact.
- `flow.md` provided by direction:

```md
(none)
```

- `api_spec.md` for this infra story:

```md
(none)
```

- Verbatim direction acceptance criteria:

```md
- [ ] When origin/main advances, the host checkout fast-forwards to origin/main (no manual step) and the four sacrifice-* user services restart to pick up the new code.
- [ ] A post-restart health check (curl -fsS http://localhost:8000/healthz) must pass; on failure the deploy alerts and does not leave services broken.
- [ ] The mechanism only redeploys on a genuine main advance (idempotent; no restart when already at origin/main) and logs each action.
- [ ] Documented: how it is triggered (poll timer or webhook) and how to disable it.
- [ ] Verified once end-to-end: a commit merged to main appears running on the deployed instance (local == remote == deployed) without manual intervention.
```

- Context to load before implementation/testing:
  - [Source: context/project.md#Identity]
  - [Source: context/project.md#Stack]
  - [Source: context/project.md#Active constraints]
  - [Source: context/navigation.md#When working on migration or machine bootstrap]
  - [Source: context/current-state.md#Deployment and runtime operations]
  - [Source: context/current-state.md#Auth and service topology]
  - [Source: context/modules/migration.md#Host bootstrap and machine state]
  - [Source: context/modules/security.md#Operational security]
  - [Source: context/modules/backend.md#Runtime and services]
- Direction-constrained implementation notes:
  - Host path is `/home/k/sacrifice`.
  - Required services are `sacrifice-backend`, `sacrifice-frontend`, `sacrifice-celery`, `sacrifice-expo-go`.
  - Health gate command is exactly `curl -fsS http://localhost:8000/healthz`.
  - Trigger mode may be either poll timer or webhook; documentation must state which was chosen and how to disable it.
  - Alert mechanism is unspecified by direction; implementation must choose the simplest host-observable path available and document it.
  - Because the direction says “does not leave services broken,” failure behavior must be explicit and reviewable rather than implied.
- Repo/process constraints:
  - Do not start uvicorn or Expo manually; orchestrator owns ports already. [Source: context/project.md#Active constraints]
  - Only involve Celery-related runtime changes if required by the restart scope already named by direction. [Source: context/project.md#Active constraints]
  - Story output is the source of truth; keep implementation aligned to the task order above.

## References
- `context/project.md`
- `context/navigation.md`
- `context/current-state.md`
- `context/modules/migration.md`
- `context/modules/security.md`
- `context/modules/backend.md`
- Direction: `direction.md`

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
