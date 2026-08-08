---
title: Expose a build-metadata endpoint so a deployed instance can be identified
type: feature
priority: p2
explore: false
created_at: '2026-08-08T08:10:00+00:00'
related_directions: []
---

# Expose a build-metadata endpoint so a deployed instance can be identified

## Why

`/api/health` answers `{"status":"ok"}` and nothing else, so there is no way to
ask a running instance *which build it is*. When the deployment was last down we
could not tell from the outside whether the process serving traffic was the
commit we thought we had shipped — the only way to find out was to shell onto the
box. An operator (and the factory's own smoke gate) needs one cheap, unauthenticated
request that answers "what is running here".

This is deliberately small. It is the first story run end to end through the
out-of-process acceptance oracle, so the value of a narrow, unambiguous surface
is that a failure is attributable to the harness rather than to ambiguity in the
spec.

## Acceptance Criteria

- [ ] `GET /api/meta` returns 200 with a JSON object whose `service` field is
  exactly the string `"sacrifice"`, so a caller can confirm which application
  answered.
- [ ] The same response includes a `version` field that is a non-empty string,
  so two deployments of different builds are distinguishable from the outside.
- [ ] The endpoint answers without any `Authorization` header — an unauthenticated
  `GET /api/meta` returns 200 and the body described above, so the smoke gate and
  an operator can call it before any login exists.

## Out of scope

- Any authenticated or per-user information. This endpoint is public by design;
  it must never include user data, request counts, environment variables, secrets,
  or database contents.
- Changing `/api/health`. It keeps its current contract; this is a second,
  separate endpoint.
- Frontend work. No UI consumes this yet.

## Context

- The FastAPI app is assembled in `backend/app/main.py`; route modules live in
  `backend/app/routes/` and are included there. `backend/app/routes/health.py` is
  the closest existing example of a tiny unauthenticated endpoint and is the right
  shape to copy.
- Application routes are prefixed `/api` (`/api/health` is the existing
  precedent).
- A version string need not come from git: a module-level constant that the
  release process can bump is sufficient for this story, provided it is non-empty.
  Do not shell out to `git` at request time.
