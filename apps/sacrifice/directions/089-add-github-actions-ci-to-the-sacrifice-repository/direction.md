---
title: Add GitHub Actions CI to the sacrifice repository
type: infra
priority: p1
explore: true
created_at: '2026-07-19T01:02:29.731931+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Add GitHub Actions CI to the sacrifice repository

## Why

xvanov/sacrifice (a repo separate from software-factory) has ZERO automated CI — no .github/workflows exist. Pushes and PRs get no lint/typecheck/test/smoke signal except whatever the factory's own merge-gate machinery runs out-of-band. This is the gap that let 'green locally / green in a mocked test' merge code that failed on the real run. GitHub Actions CI, running the same commands the factory already gates on, makes 'CI passed' a real, server-visible signal so branch protection can require it before merge.

WHAT TO BUILD: Add .github/workflows/ci.yml to the sacrifice repo, triggered on push and pull_request to main, using astral-sh/setup-uv and Python 3.12, with these jobs (stable job names so branch protection can require them):

(1) lint — CRITICAL: the existing backend is NOT fully ruff-formatted and carries pre-existing lint debt, so a whole-repo `ruff check .` / `ruff format --check .` gate would force reformatting the entire codebase (a 150-file diff) — that is WRONG and forbidden. Instead the lint job MUST be scoped so it never requires touching unrelated files. Do EITHER: (a) run ruff check + `ruff format --check` ONLY on the files changed in the PR vs the base branch (compute the changed-file list with `git diff --name-only origin/main...HEAD -- '*.py'` and pass those paths to ruff; if none, pass); OR (b) make the whole lint job ADVISORY (warning annotation, never fails the build) exactly like the typecheck job. Prefer (a). Do NOT reformat or lint-fix the existing codebase.

(2) typecheck — `cd backend && uv run mypy app`, ADVISORY (must not fail the build; emit a warning annotation, mirroring the factory's own advisory mypy job, since pre-existing findings may exist).

(3) pytest — `cd backend && uv run --extra dev pytest -q tests/` with a Postgres service container (the suite needs a real DB; mirror the services in docker-compose.yml and scripts/smoke.sh). Do NOT modify application/test source to make this pass — the suite is green on current main; if a test fails in CI it's an environment/service-wiring issue in the workflow, fix THAT, not the app code.

(4) smoke — run `make smoke` (the existing real-boot gate: boots the backend on an ephemeral port against a Postgres service and runs the register->login->create-goal->proof journey) using the same Postgres service. The migrate/boot steps must run from the correct working directory (the backend package must be importable — set the working directory to `backend/` or PYTHONPATH accordingly; a `ModuleNotFoundError: No module named 'app'` means the step ran from the wrong cwd).

Give jobs sensible timeouts. The workflow must run green on the current main of the sacrifice repo. SCOPE DISCIPLINE: this PR adds the workflow file (+ at most a tiny CI-helper). It MUST NOT reformat, lint-fix, or otherwise modify unrelated application/test source — keep the diff to the workflow and any strictly-necessary config. A ballooning diff (dozens of reformatted files) is a failure of this direction, not success.

## Acceptance Criteria

- [ ] .github/workflows/ci.yml exists and runs on push + PR to main.
- [ ] lint, pytest, and smoke jobs pass on the current main of the sacrifice repo (verify via a real Actions run that goes green before merge).
- [ ] The smoke job boots a real backend + Postgres service and exercises the real user journey (not mocked).
- [ ] typecheck runs as advisory (warning only), not a hard failure.
- [ ] Job names are stable (lint, typecheck, pytest, smoke) so branch protection can require them.
- [ ] The PR diff is MINIMAL — the workflow file plus at most strictly-necessary config. It does NOT reformat or modify unrelated application/test source (a diff touching dozens of files is a failure). The lint job is scoped to changed files (or advisory) so it never forces a whole-repo reformat.
